"""Contains code for an FadeCandy hardware for RGB LEDs."""
# fadecandy.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import json
import struct

from mpf.system.utility_functions import Util
from mpf.platform.openpixel import OpenPixelClient
from mpf.platform.openpixel import HardwarePlatform as OPHardwarePlatform


class HardwarePlatform(OPHardwarePlatform):
    """Base class for the open pixel hardware platform.

    Args:
        machine: The main ``MachineController`` object.

    """

    def __init__(self, machine):

        super(HardwarePlatform, self).__init__(machine)

        self.log = logging.getLogger("FadeCandy")
        self.log.debug("Configuring FadeCandy hardware interface.")

    def __repr__(self):
        return '<Platform.FadeCandy>'

    def _setup_opc_client(self):
        self.opc_client = FadeCandyOPClient(self.machine,
            self.machine.config['open_pixel_control'])


class FadeCandyOPClient(OpenPixelClient):
    """Base class of an OPC client which connects to a FadeCandy server.

    Args:
        machine: The main ``MachineController`` instance.
        config: Dictionary which contains configuration settings for the OPC
            client.

    This class implements some FadeCandy-specific features that are not
    available with generic OPC implementations.

    """
    def __init__(self, machine, config):

        super(FadeCandyOPClient, self).__init__(machine, config)

        self.log = logging.getLogger('FadeCandyClient')

        self.update_every_tick = True

        self.gamma = self.machine.config['led_settings']['gamma']
        self.whitepoint = Util.string_to_list(
            self.machine.config['led_settings']['whitepoint'])

        self.whitepoint[0] = float(self.whitepoint[0])
        self.whitepoint[1] = float(self.whitepoint[1])
        self.whitepoint[2] = float(self.whitepoint[2])

        self.linear_slope = (
            self.machine.config['led_settings']['linear_slope'])
        self.linear_cutoff = (
            self.machine.config['led_settings']['linear_cutoff'])
        self.keyframe_interpolation = (
            self.machine.config['led_settings']['keyframe_interpolation'])
        self.dithering = self.machine.config['led_settings']['dithering']

        if not self.dithering:
            self.disable_dithering()

        if not self.keyframe_interpolation:
            self.update_every_tick = False

        self.set_global_color_correction()
        self.write_firmware_options()

    def __repr__(self):
        return '<Platform.FadeCandyOPClient>'

    def set_gamma(self, gamma):
        """Sets the gamma correction of the FadeCandy. Specifically this is the
        exponent for the nonlinear portion of the brightness curve.

        Args:
            gamma: Float of the new gamma. Default is 2.5.

        """
        self.gamma = float(gamma)
        self.set_global_color_correction()

    def set_whitepoint(self, whitepoint):
        """Sets the white point of the FadeCandy. This is a vector of [red,
        green, blue] values to multiply by colors prior to gamma correction.

        Args:
            whitepoint: A three-item list of floating point values. Default is
                [1.0, 1.0, 1.0]

        """
        self.whitepoint = whitepoint
        self.set_global_color_correction()

    def set_linear_slope(self, linearslope):
        """Sets the linear slope (output / input) of the linear section of the
        brightness curve.

        Args:
            linearslope: Float of the new linear slope. Default is 1.0.

        """

        self.linearslope = float(linearslope)
        self.set_global_color_correction()

    def set_linear_cutoff(self, linearcutoff):
        """Sets the  of the linear cutoff of the FadeCandy.

        From the FadeCandy documentation:

            By default, brightness curves are entirely nonlinear. By setting
            `linearcutoff` to a nonzero value, though, a linear area may be
            defined at the bottom of the brightness curve.

            The linear section, near zero, avoids creating very low output
            values that will cause distracting flicker when dithered. This isn't
            a problem when the LEDs are viewed indirectly such that the flicker
            is below the threshold of perception, but in cases where the flicker
            is a problem this linear section can eliminate it entierly at the
            cost of some dynamic range. To enable the linear section, set
            `linearcutoff` to some nonzero value. A good starting point is
            1/256.0, correspnding to the lowest 8-bit PWM level.

        Args:
            linearcutoff: Float of the new linear cutoff. Default is 0.0.

        """

        self.linear_cutoff = float(linearcutoff)
        self.set_global_color_correction()

    def enable_interpolation(self):
        """Enables the FadeCandy's keyframe interpolation.

        From the FadeCandy documentation:

            By default, Fadecandy interprets each frame it receives as a
            keyframe. In-between these keyframes, Fadecandy will generate smooth
            intermediate frames using linear interpolation. The interpolation
            duration is determined by the elapsed time between when the final
            packet of one frame is received and when the final packet of the
            next frame is received.

            This scheme works well when frames are arriving at a nearly constant
            rate. If frames suddenly arrive slower than they had been arriving,
            interpolation will proceed faster than it optimally should, and one
            keyframe will hold steady until the next keyframe arrives. If frames
            suddenly arrive faster than they had been arriving, Fadecandy will
            need to jump ahead in order to avoid falling behind.

        When enabled, MPF will send an update to the FadeCandy on every machine
        tick (regardless of whether there are updates for the LEDs) in order to
        maintain a consistent update rate.

        Note that this setting is written to the FadeCandy's firmware. It will
        persist until it's changed. It is enabled by default.

        """

        self.keyframe_interpolation = True
        self.write_firmware_options()
        self.update_every_tick = True

    def disable_interpolation(self):
        """Disables the FadeCandy's keyframe interpolation.

        See the documentation for the ``enable_interpolation()`` method for a
        description of how this works.

        Note that this setting is written to the FadeCandy's firmware. It will
        persist until it's changed. It is enabled by default.

        """

        self.keyframe_interpolation = False
        self.write_firmware_options()
        self.update_every_tick = False

    def enable_dithering(self):
        """Enables the FadeCandy's smooth dithering of color values.

        Note that this setting is written to the FadeCandy's firmware. It will
        persist until it's changed. It is enabled by default.

        From the FadeCandy documentation:

            Fadecandy internally represents colors with 16 bits of precision per
            channel, or 48 bits per pixel. Why 48-bit color? In combination with
            our dithering algorithm, this gives a lot more color resolution.
            It's especially helpful near the low end of the brightness range,
            where stair-stepping and color popping artifacts can be most
            apparent.

        """

        self.dithering = True
        self.write_firmware_options()

    def disable_dithering(self):
        """Disables the FadeCandy's smooth dithering of color values.

        Note that this setting is written to the FadeCandy's firmware. It will
        persist until it's changed. It is enabled by default.

        """

        self.dithering = False
        self.write_firmware_options()

    def set_global_color_correction(self):
        """Writes the current global color correction settings (gamma, white
        point, linear slope, and linear cutoff) to the FadeCandy server.

        """

        msg = json.dumps({
                            'gamma': self.gamma,
                            'whitepoint': self.whitepoint,
                            'linearSlope': self.linear_slope,
                            'linearCutoff': self.linear_cutoff
                            })

        self.send(struct.pack(
            "!BBHHH", 0x00, 0xFF, len(msg) + 4, 0x0001, 0x0001) + msg)

    def write_firmware_options(self):
        """Writes the current firmware settings (keyframe interpolation and
        dithering) to the FadeCandy hardware.

        """
        config_byte = 0x00

        if not self.dithering:
            config_byte |= 0x01

        if not self.keyframe_interpolation:
            config_byte |= 0x02

        # manual LED control
        # config_byte = config_byte | 0x04

        # turn LED on
        # config_byte = config_byte | 0x08

        self.send(struct.pack(
            "!BBHHHB", 0x00, 0xFF, 0x0005, 0x0001, 0x0002, config_byte))


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
