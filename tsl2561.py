import time
import ustruct


_COMMAND_BIT = const(0x80)
_WORD_BIT = const(0x20)

_REGISTER_CONTROL = const(0x00)
_REGISTER_TIMING = const(0x01)
_REGISTER_ID = const(0x0A)
_REGISTER_CHANNEL0 = const(0x0C)
_REGISTER_CHANNEL1 = const(0x0E)

_CONTROL_POWERON = const(0x03)
_CONTROL_POWEROFF = const(0x00)

_INTEGRATION_TIME = {
#  time     hex     wait    clip    min     max     scale
    13:     (0x00,  15,    4900,   100,    4850,    0x7517),
    101:    (0x01,  120,   37000,  200,    36000,   0x0FE7),
    402:    (0x02,  450,   65000,  500,    63000,   1 << 10),
}


class TSL2561:
    _LUX_SCALE = (
    #       K       B       M
        (0x0040, 0x01f2, 0x01be),
        (0x0080, 0x0214, 0x02d1),
        (0x00c0, 0x023f, 0x037b),
        (0x0100, 0x0270, 0x03fe),
        (0x0138, 0x016f, 0x01fc),
        (0x019a, 0x00d2, 0x00fb),
        (0x029a, 0x0018, 0x0012),
    )

    def __init__(self, i2c, address=0x39):
        self.i2c = i2c
        self.address = address
        sensor_id = self.sensor_id()
        if sensor_id != 0x0a:
            raise RuntimeError("bad sensor id {:x}".format(sensor_id))
        self._gain = 1
        self._integration_time = 13
        self._update_gain_and_time()
        self.active(False)

    def _register16(self, register, value=None):
        if value is None:
            data = self.i2c.readfrom_mem(self.address, register, 2)
            return ustruct.unpack('<H', data)[0]
        data = ustruct.pack('<H', value)
        self.i2c.writeto_mem(self.address, register, data)

    def _register8(self, register, value=None):
        if value is None:
            return self.i2c.readfrom_mem(self.address, register, 1)[0]
        data = ustruct.pack('<B', value)
        self.i2c.writeto_mem(self.address, register, data)

    def active(self, value=None):
        if value is None:
            return self._active
        self._active = value
        self._register8(_COMMAND_BIT | _REGISTER_CONTROL,
            _CONTROL_POWERON if value else _CONTROL_POWEROFF)

    def gain(self, value=None):
        if value is None:
            return self._gain
        if value not in (1, 16):
            raise ValueError("gain must be either 1x or 16x")
        self._gain = value
        self._update_gain_and_time()

    def integration_time(self, value=None):
        if value is None:
            return self._integration_time
        if value not in _INTEGRATION_TIME:
            raise ValueError("integration time must be 13ms, 101ms or 402ms")
        self._integration_time = value
        self._update_gain_and_time()

    def _update_gain_and_time(self):
        self.active(True)
        try:
            self._register8(_COMMAND_BIT | _REGISTER_TIMING,
                _INTEGRATION_TIME[self._integration_time][0] |
                {1: 0x00, 16: 0x10}[self._gain]);
        finally:
            self.active(False)

    def sensor_id(self):
        return self._register8(_REGISTER_ID)

    def _read(self):
        self.active(True)
        try:
            time.sleep_ms(_INTEGRATION_TIME[self._integration_time][1])
            broadband = self._register16(
                _COMMAND_BIT | _WORD_BIT | _REGISTER_CHANNEL0)
            ir = self._register16(
                _COMMAND_BIT | _WORD_BIT | _REGISTER_CHANNEL1)
        finally:
            self.active(False)
        return broadband, ir

    def _lux(self, channels):
        broadband, ir = channels
        clip = _INTEGRATION_TIME[self._integration_time][2]
        if broadband > clip or ir > clip:
            raise ValueError("sensor saturated")
        scale = _INTEGRATION_TIME[self._integration_time][5] // self._gain
        channel0 = (broadband * scale) / 1024
        channel1 = (ir * scale) / 1024
        ratio = (((channel1 * 1024) / channel0 if channel0 else 0) + 1) / 2
        for k, b, m in self._LUX_SCALE:
            if ratio <= k:
                break
        else:
            b = 0
            m = 0
        return (max(0, channel0 * b - channel1 * m) + (1 << 13)) / 16384

    def read(self, autogain=False, raw=False):
        broadband, ir = self._read()
        if autogain:
            new_gain = self._gain
            if broadband < _INTEGRATION_TIME[self._integration_time][3]:
                new_gain = 16
            elif broadband > _INTEGRATION_TIME[self._integration_time][4]:
                new_gain = 1
            if new_gain != self._gain:
                self.gain(new_gain)
                broadband, ir = self._read()
        if raw:
            return broadband, ir
        return self._lux((broadband, ir))


# Those packages are identical.
TSL2561T = TSL2561
TSL2561FN = TSL2561
TSL2561CL = TSL2561


class TSL2561CS(TSL2561):
    # This package has different lux scale.
    _LUX_SCALE = (
    #       K       B       M
        (0x0043, 0x0204, 0x01ad),
        (0x0085, 0x0228, 0x02c1),
        (0x00c8, 0x0253, 0x0363),
        (0x010a, 0x0282, 0x03df),
        (0x014d, 0x0177, 0x01dd),
        (0x019a, 0x0101, 0x0127),
        (0x029a, 0x0037, 0x002b),
    )
