#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from __future__ import absolute_import
from __future__ import division
import time
import os
import yaml
import logging
import subprocess
import pkg_resources
import tables as tb
import numpy as np
import zmq

from contextlib import contextmanager
from .tpx3 import TPX3
from .fifo_readout import FifoReadout
from tables.exceptions import NoSuchNodeError
import six
from six.moves import range

VERSION = pkg_resources.get_distribution("tpx3-daq").version
loglevel = logging.getLogger('TPX3').getEffectiveLevel()


def get_software_version():
    try:
        rev = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode()
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode()
        return branch + '@' + rev
    except:
        return VERSION


class MetaTable(tb.IsDescription):
    index_start = tb.UInt32Col(pos=0)
    index_stop = tb.UInt32Col(pos=1)
    data_length = tb.UInt32Col(pos=2)
    timestamp_start = tb.Float64Col(pos=3)
    timestamp_stop = tb.Float64Col(pos=4)
    scan_param_id = tb.UInt32Col(pos=5)
    error = tb.UInt32Col(pos=6)
    trigger = tb.Float64Col(pos=7)


class RunConfigTable(tb.IsDescription):
    attribute = tb.StringCol(64)
    value = tb.StringCol(128)


class DacTable(tb.IsDescription):
    DAC = tb.StringCol(64)
    value = tb.UInt16Col()


def send_data(socket, data, scan_par_id, name='ReadoutData'):
    '''Sends the data of every read out (raw data and meta data)

        via ZeroMQ to a specified socket
    '''

    data_meta_data = dict(
        name=name,
        dtype=str(data[0].dtype),
        shape=data[0].shape,
        timestamp_start=data[1],  # float
        timestamp_stop=data[2],  # float
        error=data[3],  # int
        scan_par_id=scan_par_id
    )
    try:
        socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
        # PyZMQ supports sending numpy arrays without copying any data
        socket.send(data[0], flags=zmq.NOBLOCK)
    except zmq.Again:
        pass


class ScanBase(object):
    '''
        Basic run meta class.
        Base class for scan- / tune- / analyze-class.
    '''

    def __init__(self, dut_conf=None):

        self.proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.working_dir = os.path.join(os.getcwd(), "output_data")
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.run_name = self.timestamp + '_' + self.scan_id
        self.output_filename = os.path.join(self.working_dir, self.run_name)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(loglevel)
        self.setup_logfile()

        self.logger.info('Initializing %s...', self.__class__.__name__)

        self.chip = TPX3(dut_conf)

    def get_basil_dir(self):
        return str(os.path.dirname(os.path.dirname(basil.__file__)))

    def get_chip(self):
        return self.chip

    def prepare_injection_masks(self, start_column, stop_column, start_row, stop_row, mask_step):
        pass


    def dump_configuration(self, iteration = None, **kwargs):
        if iteration == None:
            run_config_table = self.h5_file.create_table(self.h5_file.root.configuration, name='run_config', title='Run config', description=RunConfigTable)
        else:
            run_config_table = self.h5_file.create_table(self.h5_file.root.configuration, name='run_config_' + str(iteration), title='Run config ' + str(iteration), description=RunConfigTable)
        row = run_config_table.row
        row['attribute'] = 'scan_id'
        row['value'] = self.scan_id
        row.append()
        row = run_config_table.row
        row['attribute'] = 'run_name'
        row['value'] = self.run_name
        row.append()
        row = run_config_table.row
        row['attribute'] = 'software_version'
        row['value'] = get_software_version()
        row.append()
        row = run_config_table.row
        row['attribute'] = 'board_name'
        row['value'] = self.board_name
        row.append()
        row = run_config_table.row
        row['attribute'] = 'firmware_version'
        row['value'] = self.firmware_version
        row.append()
        row = run_config_table.row
        row['attribute'] = 'chip_wafer'
        row['value'] = self.wafer_number
        row.append()
        row = run_config_table.row
        row['attribute'] = 'chip_x'
        row['value'] = self.x_position
        row.append()
        row = run_config_table.row
        row['attribute'] = 'chip_y'
        row['value'] = self.y_position
        row.append()

        run_config_attributes = ['VTP_fine_start', 'VTP_fine_stop', 'n_injections', 'n_pulse_heights', 'Vthreshold_start', 'Vthreshold_stop', 'pixeldac', 'last_pixeldac', 'last_delta', 'mask_step', 'maskfile']
        for kw, value in six.iteritems(kwargs):
            if kw in run_config_attributes:
                row = run_config_table.row
                row['attribute'] = kw
                row['value'] = value if isinstance(value, str) else str(value)
                row.append()
        run_config_table.flush()

        if iteration == None:
            dac_table = self.h5_file.create_table(self.h5_file.root.configuration, name='dacs', title='DACs', description=DacTable)
        else:
            dac_table = self.h5_file.create_table(self.h5_file.root.configuration, name='dacs_' + str(iteration), title='DACs ' + str(iteration), description=DacTable)
        for dac, value in six.iteritems(self.chip.dacs):
            row = dac_table.row
            row['DAC'] = dac
            row['value'] = value
            row.append()
        dac_table.flush()

        if iteration == None:
            self.h5_file.create_carray(self.h5_file.root.configuration, name='mask_matrix', title='Mask Matrix', obj=self.chip.mask_matrix)
            self.h5_file.create_carray(self.h5_file.root.configuration, name='thr_matrix', title='Threshold Matrix', obj=self.chip.thr_matrix)
        else:
            self.h5_file.create_carray(self.h5_file.root.configuration, name='mask_matrix_' + str(iteration), title='Mask Matrix ' + str(iteration), obj=self.chip.mask_matrix)
            self.h5_file.create_carray(self.h5_file.root.configuration, name='thr_matrix_' + str(iteration), title='Threshold Matrix ' + str(iteration), obj=self.chip.thr_matrix)

    def configure(self, **kwargs):
        '''
            Configuring step before scan start
        '''
        self.logger.info('Configuring chip...')
        #self.chip.set_dacs(**kwargs)

        self.load_mask_matrix(**kwargs)
        self.load_thr_matrix(**kwargs)

    def start(self, iteration = None, **kwargs):
        '''
            Prepares the scan and starts the actual test routine
        '''

        self._first_read = False
        self.scan_param_id = 0

        self.chip.init()
        self.fifo_readout = FifoReadout(self.chip)
        self.board_name = self.chip.board_version
        self.firmware_version = self.chip.fw_version

        # self.chip.init_communication()

        # Step 2: Chip start-up sequence
        # Step 2a: Reset the chip
        self.chip['CONTROL']['RESET'] = 1
        self.chip['CONTROL'].write()
        self.chip['CONTROL']['RESET'] = 0
        self.chip['CONTROL'].write()

        # Init communication -> set ouput mode
        data = self.chip.write_outputBlock_config()

        self.fifo_readout.reset_rx()
        self.fifo_readout.enable_rx(True)
        self.fifo_readout.print_readout_status()

        # Step 2a: Enable power pulsing
        self.chip['CONTROL']['EN_POWER_PULSING'] = 1
        self.chip['CONTROL'].write()
        self.chip['RX'].DATA_DELAY = 21

        # Step 2b: Set PLL Config
        data = self.chip.write_pll_config(write=False)
        self.chip.write(data)

        # Step 2c: Reset the Timer
        data = self.chip.getGlobalSyncHeader() + [0x40] + [0x0]
        self.chip.write(data)

        # Step 2d: Start the Timer
        data = self.chip.getGlobalSyncHeader() + [0x4A] + [0x0]
        self.chip.write(data)

        # Step 2e: Get ChipID
        data = self.chip.read_periphery_template("EFuse_Read")
        data += [0x00]*4
        self.chip["FIFO"].reset()
        time.sleep(0.1)
        self.chip.write(data)
        time.sleep(0.1)
        fdata = self.chip['FIFO'].get_data()
        dout = self.chip.decode_fpga(fdata, True)

        self.wafer_number = dout[1][19:8].tovalue()
        self.y_position = dout[1][7:4].tovalue()
        self.x_position = chr(ord('a') + dout[1][3:0].tovalue() - 1).upper()

        # Step 2f: Reset DACs
        self.chip.reset_dac_attributes(to_default = False)
        self.chip.write_dacs()

        # Step 2g: reset sequential / resets pixels?!
        # before setting PCR need to reset pixel matrix
        data = self.chip.reset_sequential(False)
        self.chip.write(data, True)
        fdata = self.chip['FIFO'].get_data()
        dout = self.chip.decode_fpga(fdata, True)
        ddout = self.chip.decode(dout[0], 0x71)
        try:
            ddout = self.chip.decode(dout[1], 0x71)
            # print ddout
        except IndexError:
            self.logger.warning("no EoR found")

        self.maskfile = kwargs.get('maskfile', None)
        self.configure(**kwargs) #TODO: all DACs set here

        # Step 3a: Produce needed PCR (Pixel conficuration)
        for i in range(256 // 4):
            self.chip.write_pcr(list(range(4 * i, 4 * i + 4)))

        #setup files
        filename = self.output_filename + '.h5'
        self.h5_file = tb.open_file(filename, mode='w', title=self.scan_id)
        self.setup_files(iteration = iteration)

        #save configuration
        self.h5_file.create_group(self.h5_file.root, 'configuration', 'Configuration')
        self.dump_configuration(iteration = iteration, **kwargs)

        # Setup data sending
        socket_addr = kwargs.pop('send_data', 'tcp://127.0.0.2:5500')
        if socket_addr:
            try:
                self.context = zmq.Context()
                self.socket = self.context.socket(zmq.PUB)  # publisher socket
                self.socket.bind(socket_addr)
                self.logger.debug('Sending data to server %s', socket_addr)
            except zmq.error.ZMQError:
                self.logger.exception('Cannot connect to socket for data sending.')
                self.socket = None
        else:
            self.socket = None

        self.scan(**kwargs)

        self.fifo_readout.print_readout_status()
        self.fifo_readout.enable_rx(False)

        # Read all important chip values and dump to yaml
        # TODO

        self.logger.info('Closing raw data file: %s', self.output_filename + '.h5')
        self.h5_file.close()

        if self.socket:
            self.logger.debug('Closing socket connection')
            self.socket.close()
            self.socket = None

    def setup_files(self, iteration = None):
        filter_raw_data = tb.Filters(complib='blosc', complevel=5, fletcher32=False)
        self.filter_tables = tb.Filters(complib='zlib', complevel=5, fletcher32=False)
        if iteration == None:
            self.raw_data_earray = self.h5_file.create_earray(self.h5_file.root, name='raw_data', atom=tb.UIntAtom(),
                                                            shape=(0,), title='raw_data', filters=filter_raw_data)
            self.meta_data_table = self.h5_file.create_table(self.h5_file.root, name='meta_data', description=MetaTable,
                                                            title='meta_data', filters=self.filter_tables)
        else:
            self.raw_data_earray = self.h5_file.create_earray(self.h5_file.root, name='raw_data_' + str(iteration), atom=tb.UIntAtom(),
                                                            shape=(0,), title='raw_data_' + str(iteration), filters=filter_raw_data)
            self.meta_data_table = self.h5_file.create_table(self.h5_file.root, name='meta_data_' + str(iteration), description=MetaTable,
                                                            title='meta_data_' + str(iteration), filters=self.filter_tables)

    def analyze(self):
        raise NotImplementedError('ScanBase.analyze() not implemented')

    def plot(self):
        raise NotImplementedError('ScanBase.plot() not implemented')

    def scan(self, **kwargs):
        raise NotImplementedError('ScanBase.scan() not implemented')

    @contextmanager
    def readout(self, *args, **kwargs):
        timeout = kwargs.pop('timeout', 30.0)

        self.start_readout(*args, **kwargs)
        yield

        self.fifo_readout.stop(timeout=timeout)

    @contextmanager
    def shutter(self):
        self.chip['CONTROL']['SHUTTER'] = 1  # TODO with self.shutter:
        self.chip['CONTROL'].write()
        yield
        self.chip['CONTROL']['SHUTTER'] = 0
        self.chip['CONTROL'].write()

    def start_readout(self, scan_param_id=0, *args, **kwargs):
        # Pop parameters for fifo_readout.start
        callback = kwargs.pop('callback', self.handle_data)
        clear_buffer = kwargs.pop('clear_buffer', False)
        fill_buffer = kwargs.pop('fill_buffer', False)
        reset_sram_fifo = kwargs.pop('reset_sram_fifo', True)
        errback = kwargs.pop('errback', self.handle_err)
        no_data_timeout = kwargs.pop('no_data_timeout', None)
        self.scan_param_id = scan_param_id
        self.fifo_readout.start(reset_sram_fifo=reset_sram_fifo, fill_buffer=fill_buffer, clear_buffer=clear_buffer,
                                callback=callback, errback=errback, no_data_timeout=no_data_timeout)

    def handle_data(self, data_tuple):
        '''
            Handling of the data.
        '''
#         get_bin = lambda x, n: format(x, 'b').zfill(n)

        total_words = self.raw_data_earray.nrows

        self.raw_data_earray.append(data_tuple[0])
        self.raw_data_earray.flush()

        len_raw_data = data_tuple[0].shape[0]
        self.meta_data_table.row['timestamp_start'] = data_tuple[1]
        self.meta_data_table.row['timestamp_stop'] = data_tuple[2]
        self.meta_data_table.row['error'] = data_tuple[3]
        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.meta_data_table.row['scan_param_id'] = self.scan_param_id

        self.meta_data_table.row.append()
        self.meta_data_table.flush()

        if self.socket:
            send_data(self.socket, data=data_tuple, scan_par_id=self.scan_param_id)

    def handle_err(self, exc):
        msg = '%s' % exc[1]
        if msg:
            self.logger.error('%s Data Errors...', msg)
        else:
            self.logger.error(' Data Errors...')

    def setup_logfile(self):
        self.fh = logging.FileHandler(self.output_filename + '.log')
        self.fh.setLevel(loglevel)
        self.fh.setFormatter(logging.Formatter("%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s"))
        for lg in six.itervalues(logging.Logger.manager.loggerDict):
            if isinstance(lg, logging.Logger):
                lg.addHandler(self.fh)

        return self.fh

    def close_logfile(self):
        for lg in six.itervalues(logging.Logger.manager.loggerDict):
            if isinstance(lg, logging.Logger):
                lg.removeHandler(self.fh)

    def save_mask_matrix(self):
        self.logger.info('Writing mask_matrix to file...')
        if not self.maskfile:
            self.maskfile = os.path.join(self.working_dir, self.timestamp + '_mask.h5')

        with tb.open_file(self.maskfile, 'a') as out_file:
            try:
                out_file.remove_node(out_file.root.mask_matrix)
            except NoSuchNodeError:
                self.logger.debug('Specified maskfile does not include a mask_matrix yet!')

            out_file.create_carray(out_file.root,
                                   name='mask_matrix',
                                   title='Matrix mask',
                                   obj=self.chip.mask_matrix)
            self.logger.info('Closing mask file: %s' % (self.maskfile))

    def save_thr_mask(self):
        self.logger.info('Writing TDAC mask to file...')
        if not self.maskfile:
            self.maskfile = os.path.join(self.working_dir, self.timestamp + '_mask.h5')

        with tb.open_file(self.maskfile, 'a') as out_file:
            try:
                out_file.remove_node(out_file.root.thr_matrix)
            except NoSuchNodeError:
                self.logger.debug('Specified maskfile does not include a thr_mask yet!')

            out_file.create_carray(out_file.root,
                                       name='thr_matrix',
                                       title='Matrix Threshold',
                                       obj=self.chip.thr_matrix)
            self.logger.info('Closing TDAC mask threshold file: %s' % (self.maskfile))


    def load_mask_matrix(self, **kwargs):
        if self.maskfile:
            self.logger.info('Loading mask_matrix file: %s' % (self.maskfile))
            try:
                with tb.open_file(self.maskfile, 'r') as infile:
                    self.chip.mask_matrix = infile.root.mask_matrix[:]
            except NoSuchNodeError:
                self.logger.debug('Specified maskfile does not include a mask_matrix!')
                pass

    def load_thr_matrix(self, **kwargs):
        if self.maskfile:
            self.logger.info('Loading thr_matrix file: %s' % (self.maskfile))
            try:
                with tb.open_file(self.maskfile, 'r') as infile:
                    self.chip.thr_matrix = infile.root.thr_matrix[:]
            except NoSuchNodeError:
                self.logger.debug('Specified maskfile does not include a thr_matrix!')
                pass


    def close(self):
        self.chip.close()
        self.close_logfile()
