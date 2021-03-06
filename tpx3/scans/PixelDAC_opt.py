#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs an equalisation of pixels based on a threshold scan
    with injected charge.
'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import os
import math
import yaml

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

from tables.exceptions import NoSuchNodeError
from io import open
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1600,
    'Vthreshold_stop'  : 2300,
    'n_injections'     : 100
}


class PixelDAC_opt(ScanBase):

    scan_id = "PixelDAC_opt"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, Vthreshold_start=1500, Vthreshold_stop=2500, n_injections=100, mask_step=16, **kwargs):
        if Vthreshold_start < 0 or Vthreshold_start > 2911:
            raise ValueError("Value {} for Vthreshold_start is not in the allowed range (0-2911)".format(Vthreshold_start))
        if Vthreshold_stop < 0 or Vthreshold_stop > 2911:
            raise ValueError("Value {} for Vthreshold_stop is not in the allowed range (0-2911)".format(Vthreshold_stop))
        if Vthreshold_stop <= Vthreshold_start:
            raise ValueError("Value for Vthreshold_stop must be bigger than value for Vthreshold_start")
        if n_injections < 1 or n_injections > 65535:
            raise ValueError("Value {} for n_injections is not in the allowed range (1-65535)".format(n_injections))
        if mask_step not in {4, 16, 64, 256}:
            raise ValueError("Value {} for mask_step is not in the allowed range (4, 16, 64, 256)".format(mask_step))

        last_delta = 1
        last_rms_delta = 22
        pixeldac = 127
        last_pixeldac = pixeldac
        iteration = 0

        # Repeat until optimization is done
        while last_delta < last_rms_delta - 2 or last_delta > last_rms_delta + 2:
            args = {
                'pixeldac'         : int(pixeldac),
                'last_pixeldac'    : int(last_pixeldac),
                'last_delta'       : float(last_delta),
                'mask_step'        : mask_step,
                'Vthreshold_start' : Vthreshold_start,
                'Vthreshold_stop'  : Vthreshold_stop,
                'n_injections'     : n_injections
            }
            if iteration != 0:
                self.setup_files(iteration = iteration)
                self.dump_configuration(iteration = iteration, **args)
            self.iterate_scan(**args)
            opt_results = self.analyze(iteration)
            last_pixeldac = pixeldac

            # Store results of iteration
            pixeldac = opt_results[0]
            last_delta = opt_results[1]
            last_rms_delta = opt_results[2]

            iteration += 1

        # Write new pixeldac into DAC YAML file
        with open('../dacs.yml') as f:
            doc = yaml.load(f, Loader=yaml.FullLoader)

        for register in doc['registers']:
            if register['name'] == 'Ibias_PixelDAC':
                register['value'] = int(pixeldac)

        with open('../dacs.yml', 'w') as f:
            yaml.dump(doc, f)

    def iterate_scan(self, pixeldac = 127, last_pixeldac = 127, last_delta = 127, Vthreshold_start=1500, Vthreshold_stop=2500, n_injections=100, mask_step=16, **kwargs):
        '''
        Threshold scan main loop

        Parameters
        ----------

        Vthreshold_fine_start : int
            TODO
        Vthreshold_fine_stop : int
            TODO

        '''

        # Set general config
        self.chip.write_general_config()

        # Write to period and phase tp registers
        data = self.chip.write_tp_period(1, 0)

        #  Write to pulse number tp register
        self.chip.write_tp_pulsenumber(n_injections)

        # Set the pixeldac to the current iteration value
        self.chip.set_dac("Ibias_PixelDAC", pixeldac)

        self.logger.info('Scan with Pixeldac %i', pixeldac)
        self.logger.info('Preparing injection masks...')

        # Create masks for pixelthreshold 0 and 15 with corresponding spacing based on 'mask_step'
        mask_cmds = []
        mask_cmds2 = []
        pbar = tqdm(total=mask_step)
        for j in range(mask_step):
            mask_step_cmd = []
            mask_step_cmd2 = []

            self.chip.test_matrix[:, :] = self.chip.TP_OFF
            self.chip.mask_matrix[:, :] = self.chip.MASK_OFF

            self.chip.test_matrix[(j//(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step))),
                                  (j%(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step)))] = self.chip.TP_ON
            self.chip.mask_matrix[(j//(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step))),
                                  (j%(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step)))] = self.chip.MASK_ON

            self.chip.thr_matrix[:, :] = 0

            for i in range(256 // 4):
                mask_step_cmd.append(self.chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

            self.chip.thr_matrix[:, :] = 15

            for i in range(256 // 4):
                mask_step_cmd2.append(self.chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())
            mask_step_cmd2.append(self.chip.read_pixel_matrix_datadriven())

            mask_cmds.append(mask_step_cmd)
            mask_cmds2.append(mask_step_cmd2)
            pbar.update(1)
        pbar.close()

        # Scan with all masks over the given threshold range for pixelthreshold 0
        cal_high_range = list(range(Vthreshold_start, Vthreshold_stop, 1))
        self.logger.info('Starting scan for THR = 0...')
        pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            # Calculate the fine and coarse threshold values
            if(vcal <= 511):
                coarse_threshold = 0
                fine_threshold = vcal
            else:
                relative_fine_threshold = (vcal - 512) % 160
                coarse_threshold = (((vcal - 512) - relative_fine_threshold) // 160) + 1
                fine_threshold = relative_fine_threshold + 352
            self.chip.set_dac("Vthreshold_coarse", coarse_threshold)
            self.chip.set_dac("Vthreshold_fine", fine_threshold)
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id):
                for i, mask_step_cmd in enumerate(mask_cmds):
                    # Only active CTPR for active columns in this iteration
                    self.chip.write_ctpr(list(range(i//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))))
                    self.chip.write(mask_step_cmd)
                    # Opening the shutter triggers the internal testpulses
                    with self.shutter():
                        time.sleep(0.01)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)
        pbar.close()

        # Scan with all masks over the given threshold range for pixelthreshold 15
        self.logger.info('Starting scan for THR = 15...')
        pbar = tqdm(total=len(mask_cmds2) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            # Calculate the fine and coarse threshold values
            if(vcal <= 511):
                coarse_threshold = 0
                fine_threshold = vcal
            else:
                relative_fine_threshold = (vcal - 512) % 160
                coarse_threshold = (((vcal - 512) - relative_fine_threshold) // 160) + 1
                fine_threshold = relative_fine_threshold + 352
            self.chip.set_dac("Vthreshold_coarse", coarse_threshold)
            self.chip.set_dac("Vthreshold_fine", fine_threshold)
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id + len(cal_high_range)):
                for i, mask_step_cmd in enumerate(mask_cmds2):
                    # Only active CTPR for active columns in this iteration
                    self.chip.write_ctpr(list(range(i//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))))
                    self.chip.write(mask_step_cmd)
                    # Opening the shutter triggers the internal testpulses
                    with self.shutter():
                        time.sleep(0.01)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)
        pbar.close()

        self.logger.info('Scan finished')

    def analyze(self, iteration = 0):
        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')
        with tb.open_file(h5_filename, 'r+') as h5_file:
            # Open raw, meta and config data
            raw_data_call = ('h5_file.root.' + 'raw_data_' + str(iteration) + '[:]')
            raw_data = eval(raw_data_call)
            meta_data_call = ('h5_file.root.' + 'meta_data_' + str(iteration) + '[:]')
            meta_data = eval(meta_data_call)
            run_config_call = ('h5_file.root.' + 'configuration.run_config_' + str(iteration) + '[:]')
            run_config = eval(run_config_call)

            # TODO: TMP this should go to analysis function with chunking
            #print('haeder1\t header2\t y\t x\t Hits\t Counter')
            self.logger.info('Interpret raw data...')
            hit_data = analysis.interpret_raw_data(raw_data, meta_data)
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
            Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]
            n_injections = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
            pixeldac = [int(item[1]) for item in run_config if item[0] == b'pixeldac'][0]
            last_pixeldac = [int(item[1]) for item in run_config if item[0] == b'last_pixeldac'][0]
            last_delta = [float(item[1]) for item in run_config if item[0] == b'last_delta'][0]

            hit_data = hit_data[hit_data['data_header'] == 1]
            param_range = np.unique(meta_data['scan_param_id'])
            hit_data_th0 = hit_data[hit_data['scan_param_id'] < len(param_range) // 2]
            param_range_th0 = np.unique(hit_data_th0['scan_param_id'])
            hit_data_th15 = hit_data[hit_data['scan_param_id'] >= len(param_range) // 2]
            param_range_th15 = np.unique(hit_data_th15['scan_param_id'])
            
            self.logger.info('Get the global threshold distributions for all pixels...')
            scurve_th0 = analysis.scurve_hist(hit_data_th0, param_range_th0)
            scurve_th15 = analysis.scurve_hist(hit_data_th15, param_range_th15)
            self.logger.info('Fit the scurves for all pixels...')
            thr2D_th0, sig2D_th0, chi2ndf2D_th0 = analysis.fit_scurves_multithread(scurve_th0, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop)), n_injections=n_injections, invert_x=True)
            thr2D_th15, sig2D_th15, chi2ndf2D_th15 = analysis.fit_scurves_multithread(scurve_th15, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop)), n_injections=n_injections, invert_x=True)

            self.logger.info('Get the cumulated global threshold distributions...')
            hist_th0 = analysis.vth_hist(thr2D_th0, Vthreshold_stop)
            hist_th15 = analysis.vth_hist(thr2D_th15, Vthreshold_stop)

            self.logger.info('Calculate new pixelDAC value...')
            pixeldac_result = analysis.pixeldac_opt(hist_th0, hist_th15, pixeldac, last_pixeldac, last_delta, Vthreshold_start, Vthreshold_stop)
            
            delta = pixeldac_result[1]
            rms_delta = pixeldac_result[2]

            # In the last iteration calculate also the equalisation matrix
            if delta > rms_delta - 2 and delta < rms_delta + 2:
                self.logger.info('Calculate the equalisation matrix...')
                eq_matrix = analysis.eq_matrix(hist_th0, hist_th15, thr2D_th0, Vthreshold_start, Vthreshold_stop)
                mask_matrix = np.zeros((256, 256), dtype=np.bool)
                mask_matrix[:, :] = 0

                self.logger.info('Writing mask_matrix to file...')
                maskfile = os.path.join(self.working_dir, self.timestamp + '_mask.h5')

                with tb.open_file(maskfile, 'a') as out_file:
                    try:
                        out_file.remove_node(out_file.root.mask_matrix)
                    except NoSuchNodeError:
                        self.logger.debug('Specified maskfile does not include a mask_matrix yet!')

                    out_file.create_carray(out_file.root,
                                        name='mask_matrix',
                                        title='Matrix mask',
                                        obj=mask_matrix)
                    self.logger.info('Closing mask file: %s' % (maskfile))

                self.logger.info('Writing equalisation matrix to file...')
                with tb.open_file(maskfile, 'a') as out_file:
                    try:
                        out_file.remove_node(out_file.root.thr_matrix)
                    except NoSuchNodeError:
                        self.logger.debug('Specified maskfile does not include a thr_mask yet!')

                    out_file.create_carray(out_file.root,
                                            name='thr_matrix',
                                            title='Matrix Threshold',
                                            obj=eq_matrix)
                    self.logger.info('Closing equalisation matrix file: %s' % (maskfile))

        self.logger.info('Result of iteration: Scan with pixeldac %i - New pixeldac %i. Delta was %f with optimal delta %f' % (int(pixeldac), int(pixeldac_result[0]), pixeldac_result[1], pixeldac_result[2]))
        return pixeldac_result


if __name__ == "__main__":
    scan = PixelDAC_opt()
    scan.start(iteration = 0, **local_configuration)
    
    
