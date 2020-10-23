from __future__ import absolute_import
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,Gdk
from matplotlib.figure import Figure
from numpy import arange, pi, random, linspace
import matplotlib.cm as cm
import numpy as np
from matplotlib.backends.backend_gtk3agg import (FigureCanvasGTK3Agg as FigureCanvas)
from gi.repository import GObject
from PlotWidget import plotwidget
from utils import utils
from logger import data_logger, file_logger, datalogger

#import time


class GUI_Plot(Gtk.Window):
    def __init__(self):
        self.active = "False"
        Gtk.Window.__init__(self, title = "Plot")
        self.connect("delete-event", self.window_destroy)
        self.set_default_size(400, 400)
        
        self.box = Gtk.Box(spacing = 6, orientation = Gtk.Orientation.HORIZONTAL)
        self.add(self.box)
        
        self.plotwidget = plotwidget()
        self.plotbox = Gtk.EventBox()
        self.plotbox.add(self.plotwidget.canvas)
        self.plotbox.connect("button_press_event", self.plot_right_clicked)
        self.box.pack_start(self.plotbox, True, True, 0)
        
        
        self.box.grid = Gtk.Grid()
        self.box.add(self.box.grid)
        self.box.grid.set_row_spacing(10)
        self.box.grid.set_column_spacing(10)
        
        self.Stopbutton = Gtk.Button(label = "Occ_Plot")
        self.Stopbutton.connect("clicked", self.on_Stopbutton_clicked)
        self.Slowbutton = Gtk.Button(label = "Slow")
        self.Slowbutton.connect("clicked", self.on_Slowbutton_clicked)
        self.Fastbutton = Gtk.Button(label = "Fast Plot")
        self.Fastbutton.connect("clicked", self.on_Fastbutton_clicked)
        self.box.grid.attach(self.Stopbutton, 0, 0, 1, 1)
        self.box.grid.attach(self.Slowbutton, 0, 1, 1, 1)
        self.box.grid.attach(self.Fastbutton, 0, 2, 1, 1)
        
        self.plotwidget.set_plottype(datalogger.read_value("plottype"))
        self.plotwidget.set_occupancy_length(datalogger.read_value("integration_length"))
        self.plotwidget.set_color_depth(datalogger.read_value("color_depth"))
        self.plotwidget.set_color_steps(datalogger.read_value("colorsteps"))
        
        if datalogger.read_value("plottype") == "normal":
            self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(datalogger.read_value("colorsteps")))
            self.Tag = GObject.idle_add(self.plotwidget.update_plot)
        elif datalogger.read_value("plottype") == "occupancy":
            self.plotwidget.change_colormap(colormap = cm.viridis, vmax = datalogger.read_value("color_depth"))
            self.plotwidget.reset_occupancy()
            self.Tag = GObject.idle_add(self.plotwidget.update_occupancy_plot)
        
        self.show_all()
        
    def on_Stopbutton_clicked(self, widget):
        GObject.source_remove(self.Tag)
        self.plotwidget.set_plottype("occupancy")
        self.plotwidget.change_colormap(colormap = cm.viridis, vmax = self.plotwidget.get_iteration_depth("occupancy.color"))
        self.plotwidget.reset_occupancy()
        self.Tag = GObject.idle_add(self.plotwidget.update_occupancy_plot)
        
    def on_Slowbutton_clicked(self, widget):
        GObject.source_remove(self.Tag)
        self.plotwidget.set_plottype("normal")
        self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(self.plotwidget.get_iteration_depth("normal")))
        self.Tag = GObject.timeout_add(500, self.plotwidget.update_plot)
        
    def on_Fastbutton_clicked(self, widget):
        GObject.source_remove(self.Tag)
        self.plotwidget.set_plottype("normal")
        self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(self.plotwidget.get_iteration_depth("normal")))
        self.Tag = GObject.idle_add(self.plotwidget.update_plot)
        
    def plot_right_clicked(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            subw = GUI_Plot_settings(self.plotwidget)
        
    def window_destroy(event, self, widget):
        datalogger.write_data(type = "plottype", value = self.plotwidget.get_plottype())
        datalogger.write_data(type = "colorsteps", value = self.plotwidget.get_iteration_depth("normal"))
        datalogger.write_data(type = "integration_length", value = self.plotwidget.get_iteration_depth("occupancy"))
        datalogger.write_data(type = "color_depth", value = self.plotwidget.get_iteration_depth("occupancy.color"))
        GObject.source_remove(self.Tag)
        self.destroy()

class GUI_Plot_settings(Gtk.Window):
    def __init__(self,plotwidget):
        Gtk.Window.__init__(self, title = "Plot Settings")
        self.connect("delete-event", self.window_destroy)
        
        color_depth = 1
        
        self.plotwidget = plotwidget
        
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        self.add(grid)
        
        if self.plotwidget.get_plottype() == "normal":
            nIteration = self.plotwidget.get_iteration_depth("normal")
            
        elif self.plotwidget.get_plottype() == "occupancy":
            nIteration = self.plotwidget.get_iteration_depth("occupancy")
            color_depth = self.plotwidget.get_iteration_depth("occupancy.color")
        
        self.OKbutton = Gtk.Button(label = "OK")
        self.OKbutton.connect("clicked", self.on_OKbutton_clicked)
        
        #Plot depth
        plot_depth_label = Gtk.Label()
        plot_depth_label.set_text("Plot Depth")
        self.plot_depth_value = nIteration
        plot_depth_adj = Gtk.Adjustment( nIteration, 0, 1000, 1, 0, 0)
        self.plot_depth = Gtk.SpinButton(adjustment = plot_depth_adj, climb_rate = 1, digits = 0)
        self.plot_depth.set_value(self.plot_depth_value) 
        self.plot_depth.connect("value-changed", self.plot_depth_set)
        
        #color depth
        color_depth_label = Gtk.Label()
        color_depth_label.set_text("Color Depth")
        self.color_depth_value = color_depth
        color_depth_adj = Gtk.Adjustment( color_depth, 0, 255, 1, 0, 0)
        self.color_depth = Gtk.SpinButton(adjustment = color_depth_adj, climb_rate = 1, digits = 0)
        self.color_depth.set_value(self.color_depth_value) 
        self.color_depth.connect("value-changed", self.color_depth_set)
        
        grid.attach(plot_depth_label, 0, 0, 3, 1)
        grid.attach(self.plot_depth, 0, 1, 3, 1)
        grid.attach(color_depth_label, 0, 2, 3, 1)
        grid.attach(self.color_depth, 0, 3, 3, 1)
        grid.attach(self.OKbutton, 3, 4, 1, 1)
        
        self.show_all()
        
        if self.plotwidget.get_plottype() == "normal":
            color_depth_label.hide()
            self.color_depth.hide()
            
    def plot_depth_set(self, event):
        self.plot_depth_value = self.plot_depth.get_value_as_int()

    def color_depth_set(self, event):
        self.color_depth_value = self.color_depth.get_value_as_int()
    
    def on_OKbutton_clicked(self, widget):
        if self.plotwidget.get_plottype() == "normal":
            self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(self.plot_depth_value))
            self.destroy()
            
        elif self.plotwidget.get_plottype() == "occupancy":
            self.plotwidget.change_colormap(colormap = cm.viridis, vmax = self.color_depth_value)
            self.plotwidget.set_occupancy_length(self.plot_depth_value)
            self.plotwidget.reset_occupancy()
            self.destroy()
        
    def window_destroy(self, widget, event):
        self.destroy()
        
class GUI_SetDAC(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = "DAC settings")
        self.connect("delete-event", self.window_destroy)
        
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        self.add(grid)
        
        
        Space = Gtk.Label()
        Space.set_text("")
        
        #Ibias_Preamp_ON
        self.Ibias_Preamp_ON_value = 127
        Ibias_Preamp_ON_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_Preamp_ON = Gtk.SpinButton(adjustment = Ibias_Preamp_ON_adj, climb_rate = 1, digits=0)
        self.Ibias_Preamp_ON.set_value(self.Ibias_Preamp_ON_value) 
        self.Ibias_Preamp_ON.connect("value-changed", self.Ibias_Preamp_ON_set)
        Ibias_Preamp_ON_label = Gtk.Label()
        Ibias_Preamp_ON_label.set_text("Ibias_Preamp_ON ")
        
        #Ibias_Preamp_OFF
        self.Ibias_Preamp_OFF_value =7
        Ibias_Preamp_OFF_adj = Gtk.Adjustment(7, 0, 15, 1, 0, 0)
        self.Ibias_Preamp_OFF = Gtk.SpinButton(adjustment = Ibias_Preamp_OFF_adj, climb_rate = 1, digits = 0)
        self.Ibias_Preamp_OFF.set_value(self.Ibias_Preamp_OFF_value) 
        self.Ibias_Preamp_OFF.connect("value-changed", self.Ibias_Preamp_OFF_set)
        Ibias_Preamp_OFF_label = Gtk.Label()
        Ibias_Preamp_OFF_label.set_text("Ibias_Preamp_OFF ")
        
        #VPreamp_NCAS
        self.VPreamp_NCAS_value = 127
        VPreamp_NCAS_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.VPreamp_NCAS = Gtk.SpinButton(adjustment = VPreamp_NCAS_adj, climb_rate = 1, digits = 0)
        self.VPreamp_NCAS.set_value(self.VPreamp_NCAS_value) 
        self.VPreamp_NCAS.connect("value-changed", self.VPreamp_NCAS_set)
        VPreamp_NCAS_label = Gtk.Label()
        VPreamp_NCAS_label.set_text("VPreamp_NCAS ")
        
        #Ibias_Ikrum
        self.Ibias_Ikrum_value = 127
        Ibias_Ikrum_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_Ikrum = Gtk.SpinButton(adjustment = Ibias_Ikrum_adj, climb_rate = 1, digits = 0)
        self.Ibias_Ikrum.set_value(self.Ibias_Ikrum_value) 
        self.Ibias_Ikrum.connect("value-changed", self.Ibias_Ikrum_set)
        Ibias_Ikrum_label = Gtk.Label()
        Ibias_Ikrum_label.set_text("Ibias_Ikrum ")
        
        #Vfbk
        self.Vfbk_value = 127
        Vfbk_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Vfbk = Gtk.SpinButton(adjustment = Vfbk_adj, climb_rate = 1, digits = 0)
        self.Vfbk.set_value(self.Vfbk_value) 
        self.Vfbk.connect("value-changed", self.Vfbk_set)
        Vfbk_label = Gtk.Label()
        Vfbk_label.set_text("Vfbk ")
        
        #Vthreshold_fine
        self.Vthreshold_fine_value = 255
        Vthreshold_fine_adj = Gtk.Adjustment(255, 0, 511, 1, 0, 0)
        self.Vthreshold_fine = Gtk.SpinButton(adjustment = Vthreshold_fine_adj, climb_rate = 1, digits = 0)
        self.Vthreshold_fine.set_value(self.Vthreshold_fine_value) 
        self.Vthreshold_fine.connect("value-changed", self.Vthreshold_fine_set)
        Vthreshold_fine_label = Gtk.Label()
        Vthreshold_fine_label.set_text("Vthreshold_fine ")
        
        #Vthreshold_coarse
        self.Vthreshold_coarse_value = 7
        Vthreshold_coarse_adj = Gtk.Adjustment(7, 0, 15, 1, 0, 0)
        self.Vthreshold_coarse = Gtk.SpinButton(adjustment = Vthreshold_coarse_adj, climb_rate = 1, digits = 0)
        self.Vthreshold_coarse.set_value(self.Vthreshold_coarse_value) 
        self.Vthreshold_coarse.connect("value-changed", self.Vthreshold_coarse_set)
        Vthreshold_coarse_label = Gtk.Label()
        Vthreshold_coarse_label.set_text("Vthreshold_coarse ")
        
        #Ibias_DiscS1_ON
        self.Ibias_DiscS1_ON_value = 127
        Ibias_DiscS1_ON_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_DiscS1_ON = Gtk.SpinButton(adjustment = Ibias_DiscS1_ON_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS1_ON.set_value(self.Ibias_DiscS1_ON_value) 
        self.Ibias_DiscS1_ON.connect("value-changed", self.Ibias_DiscS1_ON_set)
        Ibias_DiscS1_ON_label = Gtk.Label()
        Ibias_DiscS1_ON_label.set_text("Ibias_DiscS1_ON ")
        
        #Ibias_DiscS1_OFF
        self.Ibias_DiscS1_OFF_value = 7
        Ibias_DiscS1_OFF_adj = Gtk.Adjustment(7, 0, 15, 1, 0, 0)
        self.Ibias_DiscS1_OFF = Gtk.SpinButton(adjustment = Ibias_DiscS1_OFF_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS1_OFF.set_value(self.Ibias_DiscS1_OFF_value) 
        self.Ibias_DiscS1_OFF.connect("value-changed", self.Ibias_DiscS1_OFF_set)
        Ibias_DiscS1_OFF_label = Gtk.Label()
        Ibias_DiscS1_OFF_label.set_text("Ibias_DiscS1_OFF ")
        
        #Ibias_DiscS2_ON
        self.Ibias_DiscS2_ON_value = 127
        Ibias_DiscS2_ON_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_DiscS2_ON = Gtk.SpinButton(adjustment = Ibias_DiscS2_ON_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS2_ON.set_value(self.Ibias_DiscS2_ON_value) 
        self.Ibias_DiscS2_ON.connect("value-changed", self.Ibias_DiscS2_ON_set)
        Ibias_DiscS2_ON_label = Gtk.Label()
        Ibias_DiscS2_ON_label.set_text("Ibias_DiscS2_ON ")
        
        #Ibias_DiscS2_OFF
        self.Ibias_DiscS2_OFF_value = 7
        Ibias_DiscS2_OFF_adj = Gtk.Adjustment(7, 0, 15, 1, 0, 0)
        self.Ibias_DiscS2_OFF = Gtk.SpinButton(adjustment = Ibias_DiscS2_OFF_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS2_OFF.set_value(self.Ibias_DiscS2_OFF_value) 
        self.Ibias_DiscS2_OFF.connect("value-changed", self.Ibias_DiscS2_OFF_set)
        Ibias_DiscS2_OFF_label = Gtk.Label()
        Ibias_DiscS2_OFF_label.set_text("Ibias_DiscS2_OFF ")
        
        #Ibias_PixelDAC
        self.Ibias_PixelDAC_value = 127
        Ibias_PixelDAC_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_PixelDAC = Gtk.SpinButton(adjustment = Ibias_PixelDAC_adj, climb_rate = 1, digits = 0)
        self.Ibias_PixelDAC.set_value(self.Ibias_PixelDAC_value) 
        self.Ibias_PixelDAC.connect("value-changed", self.Ibias_PixelDAC_set)
        Ibias_PixelDAC_label = Gtk.Label()
        Ibias_PixelDAC_label.set_text("Ibias_PixelDAC ")
        
        #Ibias_TPbufferIn
        self.Ibias_TPbufferIn_value = 127
        Ibias_TPbufferIn_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_TPbufferIn = Gtk.SpinButton(adjustment = Ibias_TPbufferIn_adj, climb_rate = 1, digits = 0)
        self.Ibias_TPbufferIn.set_value(self.Ibias_TPbufferIn_value) 
        self.Ibias_TPbufferIn.connect("value-changed", self.Ibias_TPbufferIn_set)
        Ibias_TPbufferIn_label = Gtk.Label()
        Ibias_TPbufferIn_label.set_text("Ibias_TPbufferIn ")
        
        #Ibias_TPbufferOut
        self.Ibias_TPbufferOut_value = 127
        Ibias_TPbufferOut_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_TPbufferOut = Gtk.SpinButton(adjustment = Ibias_TPbufferOut_adj, climb_rate = 1, digits = 0)
        self.Ibias_TPbufferOut.set_value(self.Ibias_TPbufferOut_value) 
        self.Ibias_TPbufferOut.connect("value-changed", self.Ibias_TPbufferOut_set)
        Ibias_TPbufferOut_label = Gtk.Label()
        Ibias_TPbufferOut_label.set_text("Ibias_TPbufferOut ")
        
        #VTP_coarse
        self.VTP_coarse_value = 127
        VTP_coarse_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.VTP_coarse = Gtk.SpinButton(adjustment = VTP_coarse_adj, climb_rate = 1, digits = 0)
        self.VTP_coarse.set_value(self.VTP_coarse_value) 
        self.VTP_coarse.connect("value-changed", self.VTP_coarse_set)
        VTP_coarse_label = Gtk.Label()
        VTP_coarse_label.set_text("VTP_coarse ")
        
        #VTP_fine
        self.VTP_fine_value = 255
        VTP_fine_adj = Gtk.Adjustment(255, 0, 511, 1, 0, 0)
        self.VTP_fine = Gtk.SpinButton(adjustment = VTP_fine_adj, climb_rate = 1, digits = 0)
        self.VTP_fine.set_value(self.VTP_fine_value) 
        self.VTP_fine.connect("value-changed", self.VTP_fine_set)
        VTP_fine_label = Gtk.Label()
        VTP_fine_label.set_text("VTP_fine ")
        
        #Ibias_CP_PLL
        self.Ibias_CP_PLL_value = 127
        Ibias_CP_PLL_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.Ibias_CP_PLL = Gtk.SpinButton(adjustment = Ibias_CP_PLL_adj, climb_rate = 1, digits = 0)
        self.Ibias_CP_PLL.set_value(self.Ibias_CP_PLL_value) 
        self.Ibias_CP_PLL.connect("value-changed", self.Ibias_CP_PLL_set)
        Ibias_CP_PLL_label = Gtk.Label()
        Ibias_CP_PLL_label.set_text("Ibias_CP_PLL ")
        
        #PLL_Vcntrl
        self.PLL_Vcntrl_value = 127
        PLL_Vcntrl_adj = Gtk.Adjustment(127, 0, 255, 1, 0, 0)
        self.PLL_Vcntrl = Gtk.SpinButton(adjustment = PLL_Vcntrl_adj, climb_rate = 1, digits = 0)
        self.PLL_Vcntrl.set_value(self.PLL_Vcntrl_value) 
        self.PLL_Vcntrl.connect("value-changed", self.PLL_Vcntrl_set)
        PLL_Vcntrl_label = Gtk.Label()
        PLL_Vcntrl_label.set_text("PLL_Vcntrl ")
        
        #Save Button
        self.Savebutton = Gtk.Button(label = "Save")
        self.Savebutton.connect("clicked", self.on_Savebutton_clicked)
        
        
        grid.attach(Ibias_Preamp_ON_label, 0, 0, 1, 1)
        grid.attach(self.Ibias_Preamp_ON, 1, 0, 1, 1)
        grid.attach(Ibias_Preamp_OFF_label, 0, 1, 1, 1)
        grid.attach(self.Ibias_Preamp_OFF, 1, 1, 1, 1)
        grid.attach(VPreamp_NCAS_label, 0, 2, 1, 1)
        grid.attach(self.VPreamp_NCAS, 1, 2, 1, 1)
        grid.attach(Ibias_Ikrum_label, 0, 3, 1, 1)
        grid.attach(self.Ibias_Ikrum, 1, 3, 1, 1)
        grid.attach(Vfbk_label, 0, 4, 1, 1)
        grid.attach(self.Vfbk, 1, 4, 1, 1)
        grid.attach(Vthreshold_fine_label, 0, 5, 1, 1)
        grid.attach(self.Vthreshold_fine, 1, 5, 1, 1)
        grid.attach(Vthreshold_coarse_label, 0, 6, 1, 1)
        grid.attach(self.Vthreshold_coarse, 1, 6, 1, 1)
        grid.attach(Ibias_DiscS1_ON_label, 0, 7, 1, 1)
        grid.attach(self.Ibias_DiscS1_ON, 1, 7, 1, 1)
        grid.attach(Ibias_DiscS1_OFF_label, 0, 8, 1, 1)
        grid.attach(self.Ibias_DiscS1_OFF, 1, 8, 1, 1)
        grid.attach(Ibias_DiscS2_ON_label, 0, 9, 1, 1)
        grid.attach(self.Ibias_DiscS2_ON, 1, 9, 1, 1)
        grid.attach(Ibias_DiscS2_OFF_label, 0, 10, 1 , 1)
        grid.attach(self.Ibias_DiscS2_OFF, 1, 10, 1 , 1)
        grid.attach(Ibias_PixelDAC_label, 0, 11, 1, 1)
        grid.attach(self.Ibias_PixelDAC, 1, 11, 1, 1)
        grid.attach(Ibias_TPbufferIn_label, 0, 12, 1, 1)
        grid.attach(self.Ibias_TPbufferIn, 1, 12, 1, 1)
        grid.attach(Ibias_TPbufferOut_label, 0, 13, 1, 1)
        grid.attach(self.Ibias_TPbufferOut, 1, 13, 1, 1)
        grid.attach(VTP_coarse_label, 0, 14, 1, 1)
        grid.attach(self.VTP_coarse, 1, 14, 1, 1)
        grid.attach(VTP_fine_label, 0, 15, 1, 1)
        grid.attach(self.VTP_fine, 1, 15, 1, 1)
        grid.attach(Ibias_CP_PLL_label, 0, 16, 1, 1)
        grid.attach(self.Ibias_CP_PLL, 1, 16, 1, 1)
        grid.attach(PLL_Vcntrl_label, 0, 17, 1, 1)
        grid.attach(self.PLL_Vcntrl, 1, 17, 1, 1)
        ###
        grid.attach(Space, 0, 18, 1, 1)
        grid.attach(self.Savebutton, 1, 19, 1, 1)
        
        self.show_all()
        
    def Ibias_Preamp_ON_set(self, event):
        self.Ibias_Preamp_ON_value = self.Ibias_Preamp_ON.get_value_as_int()
        print("Ibias_Preamp_ON value is " + str(self.Ibias_Preamp_ON_value) + ".")
        
    def Ibias_Preamp_OFF_set(self, event):
        self.Ibias_Preamp_OFF_value = self.Ibias_Preamp_OFF.get_value_as_int()
        print("Ibias_Preamp_OFF value is " + str(self.Ibias_Preamp_OFF.get_value_as_int()) + ".")
        
    def VPreamp_NCAS_set(self, event):
        self.VPreamp_NCAS_value = self.VPreamp_NCAS.get_value_as_int()
        print("VPreamp_NCAS value is " + str(self.VPreamp_NCAS.get_value_as_int()) + ".")
        
    def Ibias_Ikrum_set(self, event):
        self.Ibias_Ikrum_value = self.Ibias_Ikrum.get_value_as_int()
        print("Ibias_Ikrum value is " + str(self.Ibias_Ikrum.get_value_as_int()) + ".")
        
    def Vfbk_set(self, event):
        self.Vfbk_value = self.Vfbk.get_value_as_int()
        print("Vfbk value is " + str(self.Vfbk.get_value_as_int()) + ".")
        
    def Vthreshold_fine_set(self, event):
        self.Vthreshold_fine_value = self.Vthreshold_fine.get_value_as_int()
        print("Vthreshold_fine value is " + str(self.Vthreshold_fine.get_value_as_int()) + ".")
        
    def Vthreshold_coarse_set(self, event):
        self.Vthreshold_coarse_value = self.Vthreshold_coarse.get_value_as_int()
        print("Vthreshold_coarse value is " + str(self.Vthreshold_coarse.get_value_as_int()) + ".")
        
    def Ibias_DiscS1_ON_set(self, event):
        self.Ibias_DiscS1_ON_value = self.Ibias_DiscS1_ON.get_value_as_int()
        print("Ibias_DiscS1_ON value is " + str(self.Ibias_DiscS1_ON.get_value_as_int()) + ".")
        
    def Ibias_DiscS1_OFF_set(self, event):
        self.Ibias_DiscS1_OFF_value = self.Ibias_DiscS1_OFF.get_value_as_int()
        print("Ibias_DiscS1_OFF value is " + str(self.Ibias_DiscS1_OFF.get_value_as_int()) + ".")
        
    def Ibias_DiscS2_ON_set(self, event):
        self.Ibias_DiscS2_ON_value = self.Ibias_DiscS2_ON.get_value_as_int()
        print("Ibias_DiscS2_ON value is " + str(self.Ibias_DiscS2_ON.get_value_as_int()) + ".")
        
    def Ibias_DiscS2_OFF_set(self, event):
        self.Ibias_DiscS2_OFF_value = self.Ibias_DiscS2_OFF.get_value_as_int()
        print("Ibias_DiscS2_OFF value is " + str(self.Ibias_DiscS2_OFF.get_value_as_int()) + ".")
        
    def Ibias_PixelDAC_set(self, event):
        self.Ibias_PixelDAC_value = self.Ibias_PixelDAC.get_value_as_int()
        print("Ibias_PixelDAC value is " + str(self.Ibias_PixelDAC.get_value_as_int()) + ".")
        
    def Ibias_TPbufferIn_set(self, event):
        self.Ibias_TPbufferIn_value = self.Ibias_TPbufferIn.get_value_as_int()
        print("Ibias_TPbufferIn value is " + str(self.Ibias_TPbufferIn.get_value_as_int()) + ".")
        
    def Ibias_TPbufferOut_set(self, event):
        self.Ibias_TPbufferOut_value = self.Ibias_TPbufferOut.get_value_as_int()
        print("Ibias_TPbufferOut value is " + str(self.Ibias_TPbufferOut.get_value_as_int()) + ".")
        
    def VTP_coarse_set(self, event):
        self.VTP_coarse_value = self.VTP_coarse.get_value_as_int()
        print("VTP_coarse value is " + str(self.VTP_coarse.get_value_as_int()) + ".")
        
    def VTP_fine_set(self, event):
        self.VTP_fine_value = self.VTP_fine.get_value_as_int()
        print("VTP_fine value is " + str(self.VTP_fine.get_value_as_int()) + ".")
        
    def Ibias_CP_PLL_set(self, event):
        self.Ibias_CP_PLL_value = self.Ibias_CP_PLL.get_value_as_int()
        print("Ibias_CP_PLL value is " + str(self.Ibias_CP_PLL.get_value_as_int()) + ".")
        
    def PLL_Vcntrl_set(self, event):
        self.PLL_Vcntrl_value = self.PLL_Vcntrl.get_value_as_int()
        print("PLL_Vcntrl value is " + str(self.PLL_Vcntrl.get_value_as_int()) + ".")
        
    def on_Savebutton_clicked(self, widget):
        print("Save DAC settings")
    
    
    def window_destroy(self, widget, event):
        self.destroy()
        
class GUI_PixelDAC_opt(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = "PixelDAC optimisation")
        self.connect("delete-event", self.window_destroy)
        
        
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)
        
        Space = Gtk.Label()
        Space.set_text("")
        
        Threshold_label = Gtk.Label()
        Threshold_label.set_text("Threshold")
        
        #Threshold_start
        self.Threshold_start_value = 200
        Threshold_start_adj = Gtk.Adjustment(200, 0, 2800, 1, 0, 0)
        self.Threshold_start = Gtk.SpinButton(adjustment = Threshold_start_adj, climb_rate = 1, digits = 0)
        self.Threshold_start.set_value(self.Threshold_start_value) 
        self.Threshold_start.connect("value-changed", self.Threshold_start_set)
        Threshold_start_label = Gtk.Label()
        Threshold_start_label.set_text("Start ")
        
        #Threshold_stop
        self.Threshold_stop_value = 1600
        Threshold_stop_adj = Gtk.Adjustment(1600, 0, 2800, 1, 0, 0)
        self.Threshold_stop = Gtk.SpinButton(adjustment = Threshold_stop_adj, climb_rate = 1, digits = 0)
        self.Threshold_stop.set_value(self.Threshold_stop_value) 
        self.Threshold_stop.connect("value-changed", self.Threshold_stop_set)
        Threshold_stop_label = Gtk.Label()
        Threshold_stop_label.set_text("Stop ")
        
        #Buttons for number of iteration
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, "4")
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "16")
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "64")
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "256")
        Iterationbutton2.set_active(True)
        Iterationbutton1.connect("toggled", self.on_Iterationbutton_toggled, "4")
        Iterationbutton2.connect("toggled", self.on_Iterationbutton_toggled, "16")
        Iterationbutton3.connect("toggled", self.on_Iterationbutton_toggled, "64")
        Iterationbutton4.connect("toggled", self.on_Iterationbutton_toggled, "256")
        
        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text("Number of iterations")
        self.Number_of_Iterations = 16
        
        #Startbutton
        self.Startbutton = Gtk.Button(label = "Start")
        self.Startbutton.connect("clicked", self.on_Startbutton_clicked)
        
        grid.attach(Threshold_label, 0, 0, 6, 1)
        grid.attach(Threshold_start_label, 0, 1, 1, 1)
        grid.attach(self.Threshold_start, 1, 1, 2, 1)
        grid.attach(Threshold_stop_label, 3, 1, 1, 1)
        grid.attach(self.Threshold_stop, 4, 1, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 2, 4, 1)
        grid.attach(Iterationbutton1, 1, 3, 1, 1)
        grid.attach(Iterationbutton2, 2, 3, 1, 1)
        grid.attach(Iterationbutton3, 3, 3, 1, 1)
        grid.attach(Iterationbutton4, 4, 3, 1, 1)
        grid.attach(Space, 0, 4, 1, 1)
        grid.attach(self.Startbutton, 4, 5, 2, 1)

        self.show_all()
        
    def Threshold_start_set(self, event):
        self.Threshold_start_value = self.Threshold_start.get_value_as_int()
        temp_Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        print("Threshold_start value is " + str(self.Threshold_start.get_value_as_int()) + ".")
        new_adjustment_start = Gtk.Adjustment(200, self.Threshold_start_value, 2800, 1, 0, 0)
        self.Threshold_stop.disconnect_by_func(self.Threshold_stop_set)
        self.Threshold_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Threshold_stop.set_value(temp_Threshold_stop_value)
        self.Threshold_stop.connect("value-changed", self.Threshold_stop_set)
        
    def Threshold_stop_set(self, event):
        self.Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        temp_Threshold_start_value = self.Threshold_start.get_value_as_int()
        print("Threshold_stop value is " + str(self.Threshold_stop.get_value_as_int()) + ".")
        new_adjustment_stop = Gtk.Adjustment(200, 0, self.Threshold_stop_value, 1, 0, 0)
        self.Threshold_start.disconnect_by_func(self.Threshold_start_set)
        self.Threshold_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Threshold_start.set_value(temp_Threshold_start_value)
        self.Threshold_start.connect("value-changed", self.Threshold_start_set)
        
    def on_Iterationbutton_toggled(self, button, name):
        if button.get_active():
            print(name, " iterations are choosen")
        self.Number_of_Iterations = int(name)
        
    def on_Startbutton_clicked(self, widget):
        print("Start PixelDAC optimisation")
        GUI.Status_window_call(function = "PixelDAC_opt", lowerTHL = self.Threshold_start_value, upperTHL = self.Threshold_stop_value, iterations = self.Number_of_Iterations)
        self.destroy()
    def window_destroy(self, widget, event):
        self.destroy()
        
class GUI_Equalisation(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = "Equalisation")
        self.connect("delete-event", self.window_destroy)
        
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)
        
        Space = Gtk.Label()
        Space.set_text("")
        
        Threshold_label = Gtk.Label()
        Threshold_label.set_text("Threshold")
        
        #Buttons for Typ of Equalisation
        Equalisation_Type_label = Gtk.Label()
        Equalisation_Type_label.set_text("Equalisation approach")
        Equalisation_Type_button1 = Gtk.RadioButton.new_with_label_from_widget(None, "Noise")
        Equalisation_Type_button1.connect("toggled", self.on_Equalisation_Typebutton_toggled, "Noise")
        Equalisation_Type_button2 = Gtk.RadioButton.new_with_label_from_widget(Equalisation_Type_button1, "Testpulse")
        Equalisation_Type_button2.connect("toggled", self.on_Equalisation_Typebutton_toggled, "Testpulse")
        self.Equalisation_Type = "Noise"
        
        #Threshold_start
        self.Threshold_start_value = 1500
        Threshold_start_adj = Gtk.Adjustment(200, 0, 2800, 1, 0, 0)
        self.Threshold_start = Gtk.SpinButton(adjustment = Threshold_start_adj, climb_rate = 1, digits = 0)
        self.Threshold_start.set_value(self.Threshold_start_value) 
        self.Threshold_start.connect("value-changed", self.Threshold_start_set)
        Threshold_start_label = Gtk.Label()
        Threshold_start_label.set_text("Start ")
        
        #Threshold_stop
        self.Threshold_stop_value = 2500
        Threshold_stop_adj = Gtk.Adjustment(1600, 0, 2800, 1, 0, 0)
        self.Threshold_stop = Gtk.SpinButton(adjustment = Threshold_stop_adj, climb_rate = 1, digits = 0)
        self.Threshold_stop.set_value(self.Threshold_stop_value) 
        self.Threshold_stop.connect("value-changed", self.Threshold_stop_set)
        Threshold_stop_label = Gtk.Label()
        Threshold_stop_label.set_text("Stop ")
        
        #Buttons for number of iteration
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, "4")
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "16")
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "64")
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "256")
        Iterationbutton2.set_active(True)
        Iterationbutton1.connect("toggled", self.on_Iterationbutton_toggled, "4")
        Iterationbutton2.connect("toggled", self.on_Iterationbutton_toggled, "16")
        Iterationbutton3.connect("toggled", self.on_Iterationbutton_toggled, "64")
        Iterationbutton4.connect("toggled", self.on_Iterationbutton_toggled, "256")
        
        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text("Number of iterations")

        self.Number_of_Iterations = 16
        
        #Startbutton
        self.Startbutton = Gtk.Button(label = "Start")
        self.Startbutton.connect("clicked", self.on_Startbutton_clicked)
        
        grid.attach(Equalisation_Type_label, 0, 0, 6, 1)
        grid.attach(Equalisation_Type_button1, 1, 1, 2, 1)
        grid.attach(Equalisation_Type_button2, 3, 1, 2, 1)
        grid.attach(Threshold_label, 0, 2, 6, 1)
        grid.attach(Threshold_start_label, 0, 3, 1, 1)
        grid.attach(self.Threshold_start, 1, 3, 2, 1)
        grid.attach(Threshold_stop_label, 3, 3, 1, 1)
        grid.attach(self.Threshold_stop, 4, 3, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 4, 4, 1)
        grid.attach(Iterationbutton1, 1, 5, 1, 1)
        grid.attach(Iterationbutton2, 2, 5, 1, 1)
        grid.attach(Iterationbutton3, 3, 5, 1, 1)
        grid.attach(Iterationbutton4, 4, 5, 1, 1)
        grid.attach(Space, 0, 6, 1, 1)
        grid.attach(self.Startbutton, 4, 7, 2, 1)

        self.show_all()
        
    def Threshold_start_set(self, event):
        self.Threshold_start_value = self.Threshold_start.get_value_as_int()
        temp_Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        print("Threshold_start value is " + str(self.Threshold_start.get_value_as_int()) + ".")
        new_adjustment_start = Gtk.Adjustment(200, self.Threshold_start_value, 2800, 1, 0, 0)
        self.Threshold_stop.disconnect_by_func(self.Threshold_stop_set)
        self.Threshold_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Threshold_stop.set_value(temp_Threshold_stop_value)
        self.Threshold_stop.connect("value-changed", self.Threshold_stop_set)
        
    def Threshold_stop_set(self, event):
        self.Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        temp_Threshold_start_value = self.Threshold_start.get_value_as_int()
        print("Threshold_stop value is " + str(self.Threshold_stop.get_value_as_int()) + ".")
        new_adjustment_stop = Gtk.Adjustment(200, 0, self.Threshold_stop_value, 1, 0, 0)
        self.Threshold_start.disconnect_by_func(self.Threshold_start_set)
        self.Threshold_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Threshold_start.set_value(temp_Threshold_start_value)
        self.Threshold_start.connect("value-changed", self.Threshold_start_set)
        
    def on_Iterationbutton_toggled(self, button, name):
        if button.get_active():
            print( name," iterations are choosen")
        self.Number_of_Iterations = int(name)
            
    def on_Equalisation_Typebutton_toggled(self, button, name):
        if button.get_active():
            print( name," based method is choosen")
        self.Equalisation_Type = name
        
    def on_Startbutton_clicked(self, widget):
        print("Start " + self.Equalisation_Type + " based Equalisation from THL=" + str(self.Threshold_start_value) + " to THL=" + 
        str(self.Threshold_stop_value) + " with " + str(self.Number_of_Iterations) + " iterations per threshold.")
        
        GUI.Status_window_call(function="Equalisation", subtype = self.Equalisation_Type, lowerTHL = self.Threshold_start_value, upperTHL = self.Threshold_stop_value, iterations = self.Number_of_Iterations)
        if self.Equalisation_Type == "Noise":
            print("Start Noise Equal")
            #Equalisation.start(self.Threshold_start_value, self.Threshold_stop_value, self.Number_of_Iterations)
        elif self.Equalisation_Type == "Testpulse":
            print("Start Charge Equal")
            #Equalisation_charge.start(self.Threshold_start_value, self.Threshold_stop_value, self.Number_of_Iterations)
            
        self.window_destroy(self)
        
    def window_destroy(self, widget, event):
        self.destroy()
        
class GUI_ToT_Calib(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = "ToT Calibration")
        self.connect("delete-event", self.window_destroy)
        
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)
        
        Space = Gtk.Label()
        Space.set_text("")
        
        Testpulse_range_label = Gtk.Label()
        Testpulse_range_label.set_text("Testpulse range")
        
        
        #Testpulse_range_start
        self.Testpulse_range_start_value = 210
        Testpulse_range_start_adj = Gtk.Adjustment(210, 0, 511, 1, 0, 0)
        self.Testpulse_range_start = Gtk.SpinButton(adjustment = Testpulse_range_start_adj, climb_rate = 1, digits = 0)
        self.Testpulse_range_start.set_value(self.Testpulse_range_start_value) 
        self.Testpulse_range_start.connect("value-changed", self.Testpulse_range_start_set)
        Testpulse_range_start_label = Gtk.Label()
        Testpulse_range_start_label.set_text("Start ")
        
        #Testpulse_range_stop
        self.Testpulse_range_stop_value = 510
        Testpulse_range_stop_adj = Gtk.Adjustment(510, 0, 511, 1, 0, 0)
        self.Testpulse_range_stop = Gtk.SpinButton(adjustment = Testpulse_range_stop_adj, climb_rate = 1, digits = 0)
        self.Testpulse_range_stop.set_value(self.Testpulse_range_stop_value) 
        self.Testpulse_range_stop.connect("value-changed", self.Testpulse_range_stop_set)
        Testpulse_range_stop_label = Gtk.Label()
        Testpulse_range_stop_label.set_text("Stop ")
        
        #Buttons for number of iteration
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, "4")
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "16")
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "64")
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, "256")
        Iterationbutton3.set_active(True)
        Iterationbutton1.connect("toggled", self.on_Iterationbutton_toggled, "4")
        Iterationbutton2.connect("toggled", self.on_Iterationbutton_toggled, "16")
        Iterationbutton3.connect("toggled", self.on_Iterationbutton_toggled, "64")
        Iterationbutton4.connect("toggled", self.on_Iterationbutton_toggled, "256")
        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text("Number of iterations")

        self.Number_of_Iterations = 64
        
        #Startbutton
        self.Startbutton = Gtk.Button(label = "Start")
        self.Startbutton.connect("clicked", self.on_Startbutton_clicked)
        

        grid.attach(Testpulse_range_label, 0, 0, 6, 1)
        grid.attach(Testpulse_range_start_label, 0, 1, 1, 1)
        grid.attach(self.Testpulse_range_start, 1, 1, 2, 1)
        grid.attach(Testpulse_range_stop_label, 3, 1, 1, 1)
        grid.attach(self.Testpulse_range_stop, 4, 1, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 2, 4, 1)
        grid.attach(Iterationbutton1, 1, 3, 1, 1)
        grid.attach(Iterationbutton2, 2, 3, 1, 1)
        grid.attach(Iterationbutton3, 3, 3, 1, 1)
        grid.attach(Iterationbutton4, 4, 3, 1, 1)
        grid.attach(Space, 0, 4, 1, 1)
        grid.attach(self.Startbutton, 4, 5, 2, 1)

        self.show_all()
        
    def Testpulse_range_start_set(self, event):
        self.Testpulse_range_start_value = self.Testpulse_range_start.get_value_as_int()
        temp_Testpulse_range_stop_value = self.Testpulse_range_stop.get_value_as_int()
        print("Testpulse_range_start value is " + str(self.Testpulse_range_start.get_value_as_int()) + ".")
        new_adjustment_start = Gtk.Adjustment(200, self.Testpulse_range_start_value, 2800, 1, 0, 0)
        self.Testpulse_range_stop.disconnect_by_func(self.Testpulse_range_stop_set)
        self.Testpulse_range_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Testpulse_range_stop.set_value(temp_Testpulse_range_stop_value)
        self.Testpulse_range_stop.connect("value-changed", self.Testpulse_range_stop_set)
        
    def Testpulse_range_stop_set(self, event):
        self.Testpulse_range_stop_value = self.Testpulse_range_stop.get_value_as_int()
        temp_Testpulse_range_start_value = self.Testpulse_range_start.get_value_as_int()
        print("Testpulse_range_stop value is " + str(self.Testpulse_range_stop.get_value_as_int()) + ".")
        new_adjustment_stop = Gtk.Adjustment(200, 0, self.Testpulse_range_stop_value, 1, 0, 0)
        self.Testpulse_range_start.disconnect_by_func(self.Testpulse_range_start_set)
        self.Testpulse_range_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Testpulse_range_start.set_value(temp_Testpulse_range_start_value)
        self.Testpulse_range_start.connect("value-changed", self.Testpulse_range_start_set)
        
    def on_Iterationbutton_toggled(self, button, name):
        if button.get_active():
            print( name," iterations are choosen")
        self.Number_of_Iterations = int(name)
        
    def on_Startbutton_clicked(self, widget):
        print("Start ToT calibration for testpulses from " + str(self.Testpulse_range_start_value * 0.5) + "\u200AmV to " + 
        str(self.Testpulse_range_stop_value * 0.5) + "\u200AmV with " + str(self.Number_of_Iterations) + " iterations per threshold.")
        
        GUI.Status_window_call(function = "ToT_Calib", lowerTHL = self.Testpulse_range_start_value, upperTHL = self.Testpulse_range_stop_value, iterations = self.Number_of_Iterations)
        
        #ToTCalib.start(VTP_fine_start = self.Testpulse_range_start_value, VTP_fine_stop = self.Testpulse_range_stop_value, mask_step = self.Number_of_Iterations)
        
        print("Start ToT Calibration")
        
        self.window_destroy(self)
        
    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Main_Settings(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = "Edit")
        self.connect("delete-event", self.window_destroy)
            
        self.input_window = None
        
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        self.add(grid)
        
        self.load_backup_button = Gtk.Button(label = "Load Backup")
        self.load_backup_button.connect("clicked", self.on_load_backup_button_clicked)
        
        self.load_default_button = Gtk.Button(label = "Load Default")
        self.load_default_button.connect("clicked", self.on_load_default_button_clicked)
        
        grid.attach(self.load_backup_button, 0, 0, 1, 1)
        grid.attach(self.load_default_button, 0, 1, 1, 1)
        
        self.show_all()
        
        
    def on_load_backup_button_clicked(self, widget):
        print("Load backup")
        self.input_window = GUI_Main_Settings_Backup_Input()
        self.input_window.connect("destroy", self.window_destroy)
        
    def on_load_default_button_clicked(self, widget):
        data = datalogger.default_config()
        datalogger.set_data(data)
        GUI.set_destroyed()
        self.destroy()
        
    def window_destroy(self, widget, event = True):
        GUI.set_destroyed()
        if self.input_window is not None:
            self.input_window.window_destroy(widget)
        self.destroy()
        
class GUI_Main_Settings_Backup_Input(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title = "")
        self.connect("delete-event", self.window_destroy)
        self.set_decorated(False)
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        self.add(grid)
        label = Gtk.Label()
        label.set_text("Enter backup file name")
        self.entry = Gtk.Entry()
        self.entry.connect('activate', self.entered_text)
        
        grid.attach(label, 0, 0, 1, 1)
        grid.attach(self.entry, 0, 1, 1, 1)
        
        self.show_all()
        
    def entered_text(self, widget):
        filename = self.entry.get_text()
        data = file_logger.read_backup("backup/" + filename)
        if not data == False:
            datalogger.set_data(data)
        self.destroy()
        
    def window_destroy(self, widget):
        self.destroy()
        
        
        
class GUI_Main(Gtk.Window):
    
    def __init__(self):
        self.open = False
        
        Gtk.Window.__init__(self, title = "Gui")
        self.set_icon_from_file(r"GasDet3.png")
        #self.set_default_size(800, 600)
        self.connect("button_press_event", self.window_on_button_press_event)
        
        self.grid = Gtk.Grid()
        self.add(self.grid)
        
        
        self.statusbar = Gtk.Statusbar()
        self.context_id = self.statusbar.get_context_id("Status Main")
        self.statusbar.push(self.context_id, "Statusbar for Markus...")
        
        self.notebook = Gtk.Notebook()
        self.grid.add(self.notebook)
        self.grid.attach(self.statusbar, 0, 1, 1, 1)
        
        #get last backup
        data = file_logger.read_backup()
        datalogger.set_data(data)
        
#########################################################################################################
        ### Page 1
        
        page1 = Gtk.Box()
        self.notebook.append_page(page1, Gtk.Label("Basic Funktion"))
        page1.set_border_width(10)
        page1.grid = Gtk.Grid()
        page1.grid.set_row_spacing(2)
        page1.grid.set_column_spacing(10)
        page1.grid.set_column_homogeneous(True)
        page1.grid.set_row_homogeneous(True)
        page1.add(page1.grid)
        
        Space = Gtk.Label()
        Space.set_text("")
        
        Space2 = Gtk.Label()
        Space2.set_text("")
        
        self.PixelDACbutton = Gtk.Button(label = "PixelDAC")
        self.PixelDACbutton.connect("clicked", self.on_PixelDACbutton_clicked)
        
        self.Equalbutton = Gtk.Button(label = "Equalisation")
        self.Equalbutton.connect("clicked", self.on_Equalbutton_clicked)
        
        self.THLScanbutton = Gtk.Button(label = "THL Calibration")
        self.THLScanbutton.connect("clicked", self.on_THLScanbutton_clicked)
        
        self.TOTScanbutton = Gtk.Button(label = "TOT Calibration")
        self.TOTScanbutton.connect("clicked", self.on_TOTScanbutton_clicked)
        
        self.Runbutton = Gtk.Button(label = "Start readout")
        self.Runbutton.connect("clicked", self.on_Runbutton_clicked)
        
        self.Startupbutton = Gtk.Button(label = "Startup Sequence")
        self.Startupbutton.connect("clicked", self.on_Startupbutton_clicked)
        
        self.Resetbutton = Gtk.Button(label = "Reset")
        self.Resetbutton.connect("clicked", self.on_Resetbutton_clicked)
        
        self.SetDACbutton = Gtk.Button(label = "Set DACs")
        self.SetDACbutton.connect("clicked", self.on_SetDACbutton_clicked)
        
        self.QuitCurrentFunctionbutton = Gtk.Button(label = "Quit")
        self.QuitCurrentFunctionbutton.connect("clicked", self.on_QuitCurrentFunctionbutton_clicked)
        
        
        Status = Gtk.Frame()
        self.Statusbox = Gtk.Box(orientation = Gtk.Orientation.VERTICAL, spacing = 6)
        Status.add(self.Statusbox)
        self.progressbar = Gtk.ProgressBar()
        self.statuslabel = Gtk.Label()
        self.statuslabel2 = Gtk.Label()
        self.statuslabel3 = Gtk.Label()
        self.statuslabel.set_text("")
        self.statuslabel2.set_text("")
        self.statuslabel3.set_text("")
        self.statuslabel2.set_justify(Gtk.Justification.LEFT)
        self.statuslabel3.set_justify(Gtk.Justification.LEFT)
        self.Statusbox.add(self.statuslabel)
        self.Statusbox.add(self.statuslabel2)
        self.Statusbox.add(self.statuslabel3)
        self.Statusbox.pack_end(self.progressbar, True, True, 5)
        
        
        page1.grid.attach(self.PixelDACbutton, 0, 0, 2, 1)
        page1.grid.attach(self.Equalbutton, 0, 1, 2, 1)
        page1.grid.attach(self.THLScanbutton, 0, 2, 2, 1)
        page1.grid.attach(self.TOTScanbutton, 0, 3, 2, 1)
        page1.grid.attach(self.Runbutton, 0, 4, 2, 2)
        page1.grid.attach(Status, 2, 5, 6, 4)
        page1.grid.attach(Space, 0, 6, 2, 2)
        page1.grid.attach(self.Startupbutton, 0, 8, 2, 1)
        page1.grid.attach(self.Resetbutton, 0, 9, 2, 1)
        page1.grid.attach(Space2, 2, 0, 6, 2)
        page1.grid.attach(self.SetDACbutton, 8, 0, 2, 1)
        page1.grid.attach(self.QuitCurrentFunctionbutton, 8, 9, 2, 1)
    
#######################################################################################################     
        ### Page 2 
        
        ChipName = "Chip1"
        TestString = "Enter Something"
        self.page2 = Gtk.Box()
        self.notebook.append_page(self.page2, Gtk.Label(ChipName))
        self.page2.set_border_width(10)
        self.page2.grid = Gtk.Grid()
        self.page2.grid.set_row_spacing(10)
        self.page2.grid.set_column_spacing(10)
        self.page2.add(self.page2.grid)
        self.page2.entry = Gtk.Entry()
        self.page2.entry.connect('activate', self.entered_text)
        self.page2.space =Gtk.Label()
        self.page2.space.set_text("         ")
        self.page2.space1 =Gtk.Label()
        self.page2.space1.set_text("    ")
        
        self.page2.label = Gtk.Label(TestString)
        self.plotbutton = Gtk.Button(label = "Show Plot")
        self.plotbutton.connect("clicked", self.on_plotbutton_clicked)
        self.page2.grid.attach(self.page2.entry, 0, 0, 1, 1)
        self.page2.grid.attach(self.page2.label, 0, 1, 1, 1)
        self.page2.grid.attach(self.plotbutton, 0, 2, 1, 1)
        
        self.plotwidget = plotwidget()
        self.page2.pack_end(self.plotwidget.canvas, True, False, 0)
        self.page2.pack_end(self.page2.space, True, False, 0)
        self.page2.pack_end(self.page2.space1, True, False, 0)
        GObject.timeout_add(250, self.plotwidget.update_plot)
        
    
################################################################################################### 
    ### Overall window event
    
    def window_on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3 and self.open == False:
            self.open = True
            self.settingwindow = GUI_Main_Settings()
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1 and self.open == True:
            self.settingwindow.window_destroy(widget = widget, event = event)
            
    def set_destroyed(self):
        self.open = False

####################################################################################################        
    ### Functions Page 1    
        
    def on_PixelDACbutton_clicked(self, widget):
        print("Function call: PixelDac_opt")
        subw = GUI_PixelDAC_opt()
        
    def on_Equalbutton_clicked(self, widget):
        print("Function call: Equalisation")
        subw = GUI_Equalisation()
        
    def on_THLScanbutton_clicked(self, widget):
        print("Function call: THLScan")
        
    def on_TOTScanbutton_clicked(self, widget):
        print("Function call: TOTScan")
        subw = GUI_ToT_Calib()
        
    def on_Runbutton_clicked(self, widget):
        print("Function call: Run")

    def on_Startupbutton_clicked(self, widget):
        print("Function call: Startup")
        
    def on_Resetbutton_clicked(self, widget):
        print("Function call: Reset")
        
    def on_SetDACbutton_clicked(self, widget):
        subw = GUI_SetDAC()
        
    def on_QuitCurrentFunctionbutton_clicked(self, widget):
        print("Function call: Quit current function")
        self.progressbar.hide()
        self.statuslabel.set_text("")
        self.statuslabel2.set_text("")
        self.statuslabel3.set_text("")
        self.progressbar.set_fraction(0.0)
        
    def Status_window_call(self, function = "default", subtype = "", lowerTHL = 0, upperTHL = 0, iterations = 0, statusstring = "", progress = 0):
        if function == "PixelDAC_opt":
            self.statuslabel.set_markup("<big><b>PixelDAC optimisation</b></big>")
            self.progressbar.show()
            self.progressbar.set_fraction(progress)
            self.statuslabel2.set_text("From THL=" + str(lowerTHL) + " to THL= " + str(upperTHL) + " with " + str(iterations) + " iterations per step")
            self.statuslabel3.set_text(statusstring)
        elif function == "Equalisation":
            self.statuslabel.set_markup("<big><b>" + subtype + "-based Equalisation</b></big>")
            self.progressbar.show()
            self.statuslabel2.set_text("From THL=" + str(lowerTHL) + " to THL= " + str(upperTHL) + " with " + str(iterations) + " iterations per step")
            self.statuslabel3.set_text(statusstring)
            self.progressbar.set_fraction(progress)
        elif function == "ToT_Calib":
            self.statuslabel.set_markup("<big><b>ToT calibration</b></big>")
            self.progressbar.show()
            self.statuslabel2.set_text("For testpulses ranging from " + utils.print_nice(lowerTHL * 0.5) + "\u200AmV to " + utils.print_nice(upperTHL * 0.5) + "\u200AmV with " + str(iterations) + " iterations per step")
            self.statuslabel3.set_text(statusstring)
            self.progressbar.set_fraction(progress)
        elif function == "status":
            self.statuslabel3.set_text(statusstring)
        elif function == "progress":
            self.progressbar.set_fraction(progress)
        elif function == "default":
            self.statuslabel.set_text("Error: Call without functionname")
            print("Error: Call without functionname")
        else:
            self.statuslabel.set_text("Error: " + function + " is not known!")
            print("Error: " + function + " is not known")


    def write_statusbar(self, status):
        self.statusbar.push(self.context_id, str(status))


########################################################################################################################
    ### Functions Page2
    
    def on_plotbutton_clicked(self, widget):
        subw = GUI_Plot()
        
    def entered_text(self, widget):
        ChipName = self.page2.entry.get_text()
        print(ChipName)
        self.notebook.set_tab_label_text(self.page2, ChipName)
        
        
########################################################################################################################        
    ### Functions right click menu
    
    def on_load_backup_clicked(self, widget):
        print("Load Backup")
        
    def on_load_default_clicked(self, widget):
        print("Set to default")
        
        
def quit_procedure(gui):
    file = file_logger.create_file()
    file_logger.write_backup(file)
    Gtk.main_quit()

if __name__ == "__main__":
    GUI = GUI_Main()
    GUI.connect("destroy", quit_procedure)
    GUI.show_all()
    GUI.progressbar.hide()
    Gtk.main()
