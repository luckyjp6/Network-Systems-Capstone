from setting import Setting
from protocols import aloha, slotted_aloha, csma, csma_cd

setting = Setting(host_num=3, total_time=100, packet_num=4, max_colision_wait_time=20, p_resend=0.3, packet_size=3, link_delay=1, seed=None)

aloha_rates = aloha(setting, True)
print(aloha_rates)

slotted_aloha_rates = slotted_aloha(setting, True)
print(slotted_aloha_rates)

csma_rates = csma(setting, True)
print(csma_rates)

csma_cd_rates = csma_cd(setting, True)
print(csma_cd_rates)