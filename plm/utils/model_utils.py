
try:
    import torch
    import torch_npu
except ImportError:
    pass

def get_vram(device):
    if torch.cuda.is_available() and str(device).startswith("cuda"):
        total_memory = torch.cuda.get_device_properties(device).total_memory / (1024 ** 3)  # 将字节转换为 GB
        return total_memory
    elif str(device).startswith("npu"):
        if torch_npu.npu.is_available():
            total_memory = torch_npu.npu.get_device_properties(device).total_memory / (1024 ** 3)  # 转为 GB
            return total_memory
    else:
        return None