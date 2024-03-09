import numpy as np
# from numba import njit


NUM_PTS = 16384

# @njit(cache=True)
def square(
    total_time, 
    upper, 
    lower, 
    frequency, 
    duty_cycle=0.5, 
    num_cycles=-1, 
    delay=0, 
    rest_v=0.
):
    buffer = np.zeros(NUM_PTS)
    time_seq = np.zeros(NUM_PTS)

    for i in range(NUM_PTS):
        t = i * total_time / (NUM_PTS - 1)
        time_seq[i] = t
        buffer[i] = square_impl(
            t, upper, lower, frequency, duty_cycle, num_cycles, 
            delay, rest_v
        )
    return time_seq, buffer


# @njit(cache=True)
def square_impl(
    t, 
    upper, 
    lower, 
    frequency, 
    duty_cycle, 
    num_cycles, 
    delay, 
    rest_v
):
    v = 0.0
    T = 1.0 / frequency
    if num_cycles < 0:
        finish_time = np.inf
    else:
        finish_time = delay + num_cycles * T

    if t < delay or t > finish_time:
        v = rest_v
    else:
        phase = ((t - delay) % T) / T
        if phase <= duty_cycle:
            v = upper
        else:
            v = lower
    return v


# @njit(cache=True)
def triangle(
    total_time, 
    upper, 
    lower, 
    frequency, 
    phase, 
    num_cycles=-1, 
    delay=0, 
    rest_v=0.
):
    buffer = np.zeros(NUM_PTS)
    time_seq = np.zeros(NUM_PTS)

    for i in range(NUM_PTS):
        t = i * total_time / (NUM_PTS - 1)
        time_seq[i] = t
        buffer[i] = triangle_impl(
            t, upper, lower, frequency, phase, num_cycles, 
            delay, rest_v
        )
    return time_seq, buffer


# @njit(cache=True)
def triangle_impl(
    t, 
    upper, 
    lower, 
    frequency, 
    phase, 
    num_cycles, 
    delay, 
    rest_v
):
    v = 0.0
    T = 1.0 / frequency
    if num_cycles < 0:
        finish_time = np.inf
    else:
        finish_time = delay + num_cycles * T

    dc = (upper + lower) / 2.0
    amp = (upper - lower) / 2.0

    if t < delay or t > finish_time:
        v = rest_v
    else:
        phase_new = ((t - delay + phase * T) % T) / T
        if phase_new <= 0.5:
            v = amp * (phase_new - 0.25) * 4 + dc
        else:
            v = -amp * (phase_new - 0.75) * 4 + dc
    return v


def pulse(total_time, amps=[], widths=[], gaps=[], delay=0., rest_v=0.):
    time_seq = np.linspace(0, total_time, num=NUM_PTS, endpoint=True)
    resolution = float(total_time) / NUM_PTS
    buffer = np.zeros(NUM_PTS)
    buffer.fill(rest_v)

    seg_start_time = np.cumsum(np.asarray(widths) + np.asarray(gaps)) + delay
    seg_start_time = np.roll(seg_start_time, 1)
    seg_start_time[0] = delay

    seg_start_idx = np.round(seg_start_time / resolution).astype(np.int32)
    seg_len = np.round(np.asarray(widths) / resolution).astype(np.int32)

    for amp, sidx, sl in zip(amps, seg_start_idx, seg_len):
        if sidx >= NUM_PTS:
            break
        buffer[sidx:sidx+sl] = amp
    return time_seq, buffer


# @njit(cache=True)
def user_impl_loop_wrapper(total_time, user_impl):
    buffer = np.zeros(NUM_PTS)
    time_seq = np.zeros(NUM_PTS)

    for i in range(NUM_PTS):
        t = i * total_time / NUM_PTS
        time_seq[i] = t
        buffer[i] = user_impl(t)
    
    return time_seq, buffer


class User(object):
    TOTAL_TIME_NAME = "Tmax"
    IMPL_FUNC_NAME = "user_impl"
    TEMPLATE = (
        "import math\n\n{} = 10\ndef {}(t):\n    return math.sqrt(t)\n"
        .format(TOTAL_TIME_NAME, IMPL_FUNC_NAME)
    )

    def __init__(self):
        self.update(self.TEMPLATE)
    
    @classmethod
    def parse_impl(cls, impl_str: str):
        assert cls.TOTAL_TIME_NAME in impl_str, (
            "`{}` not found in string, cannot determine total time."
            .format(cls.TOTAL_TIME_NAME)
        )
        assert cls.IMPL_FUNC_NAME in impl_str, (
            "`{}` not found in string, cannot recognize implementation."
            .format(cls.IMPL_FUNC_NAME)
        )

        local_scopes = {}
        exec(impl_str, local_scopes)
        total_time = float(local_scopes[cls.TOTAL_TIME_NAME])
        # user_impl = njit(local_scopes[cls.IMPL_FUNC_NAME])
        user_impl = local_scopes[cls.IMPL_FUNC_NAME]
        return total_time, user_impl
    
    def update(self, impl_str: str):
        self.user_impl_str = impl_str
        self.total_time, self.user_impl = self.parse_impl(impl_str)
        return self
    
    def __call__(self):
        return user_impl_loop_wrapper(self.total_time, self.user_impl)

