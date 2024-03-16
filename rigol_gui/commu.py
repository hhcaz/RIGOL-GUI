import numpy as np
from typing import Tuple
from pyvisa.resources.messagebased import MessageBasedResource


def query_state_cmd(ch=1):
    return ":OUTP{}?".format(ch)


def set_state_cmd(state, ch=1):
    state = "ON" if state == 1 else "OFF"
    return ":OUTP{} {}".format(ch, state)


def apply_user_cmd(freq, amp, offset, phase, ch=1):
    return ":SOUR{}:APPL:USER {},{},{},{}".format(
        ch, freq, amp, offset, phase
    )


def transfer_int_data_cmd(data):
    num_pts = len(data)
    data = np.asarray(data, dtype="<H")
    assert data.min() >= 0 and data.max() <= 2**14-1
    assert num_pts <= 2**14, "Data length should be le than {}".format(2**14)

    head = ":DATA:DAC VOLATILE,#{:d}{:d}".format(len(str(num_pts*2)), num_pts*2)
    message = head.encode("ascii") + data.tobytes()

    return message


def transfer_float_data_cmd(data):
    data = np.asarray(data, dtype=np.float32)
    assert data.min() >= -1 and data.max() <= 1

    # map [-1, 1) to [0x0000, 0x3FFF (16383)]
    data = (data + 1) / 2.0 * (2**14 - 1)
    data = np.round(data).astype("<H")

    return transfer_int_data_cmd(data)


def tranfer_wave_cmd(total_time: float, data: np.ndarray, ch=1):
    data_len = len(data)
    assert data_len <= 2**14, "Data length should be le than {}".format(2**14)

    if data_len < 2**14:
        # interpolate if data length is less than 2**14
        fx = np.linspace(0, 1, num=data_len, endpoint=True)
        interp_x = np.linspace(0, 1, num=2**14, endpoint=True)
        data = np.interp(interp_x, fx, data)
    
    freq = 1.0 / total_time
    amp = np.max(np.abs(data))
    data = np.clip(data/amp, -1, 1)
    offset = phase = 0

    messages = (
        apply_user_cmd(freq, amp*2, offset, phase, ch),
        transfer_float_data_cmd(data)
    )

    return messages


class DummyInstance(object):
    def __init__(self):
        self.states = {1: 0, 2: 0}

    def query(self, msg: str):
        if msg.startswith(":OUTP"):
            ch = int(msg[5])
            if self.states[ch] == 1:
                state = "ON"
            else:
                state = "OFF"
            return state
    
    def write(self, msg: str):
        if msg.startswith(":OUTP"):
            ch = int(msg[5])
            state = msg.split()[-1]
            if state.lower() == "on":
                self.states[ch] = 1
            else:
                self.states[ch] = 0
    
    def write_raw(self, msg: bytes):
        pass

    def close(self):
        pass


class DeviceManagerImpl(object):
    def __init__(self, inst: MessageBasedResource, channel=1):
        self.inst = inst
        self.channel = channel
        self._t = None
        self._v = None
    
    @property
    def state(self):
        msg = query_state_cmd(self.channel)
        ret = self.inst.query(msg)
        if "on" in ret.lower():
            state = 1
        else:
            state = 0
        return state
    
    @state.setter
    def state(self, on: bool):
        msg = set_state_cmd(on, self.channel)
        self.inst.write(msg)
    
    @property
    def data(self):
        if self._t is None or self._v is None:
            return None, None
        else:
            return self._t, self._v.copy()

    @data.setter
    def data(self, data: Tuple[float, np.ndarray]):
        t, v = data
        msgs = tranfer_wave_cmd(t, v, self.channel)
        for msg in msgs:
            if isinstance(msg, str):
                self.inst.write(msg)
            elif isinstance(msg, bytes):
                self.inst.write_raw(msg)
        self._t = t
        self._v = v.copy()


class DeviceManager(object):
    def __init__(self, inst: MessageBasedResource):
        self.inst = inst
    
    def __getitem__(self, ch: int) -> DeviceManagerImpl:
        assert ch in [1, 2], "Only allows openrations on channel 1 or 2"
        return DeviceManagerImpl(self.inst, ch)
    
    @classmethod
    def dummy(cls):
        return cls(DummyInstance())

