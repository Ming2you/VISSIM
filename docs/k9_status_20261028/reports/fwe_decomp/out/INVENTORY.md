# INVENTORY — D-K9-106 팔·파일·캐시 목록 (fwe_inventory.py 출력을 옮긴 표)

- 만든 도구: `fwe_decomp/tools/fwe_inventory.py`(sha256 `19316cfc5219dbd348ec3ee834e9a12b668436c91e53b0c266bd484ebe2dc04c`), 이 표: `fwe_inventory_md.py`(`2741c59ffaa2c4faffa604856fb65e211802802eddce83e18130503e880c3441`). 원본 JSON: `out/inventory.json`(`f51abd202cef209d1b1b5e79b4d3eb4ea13661fe9e0d2ec7d68bd8c5467c94e6`).
- 시드는 폴더 이름이 아니라 provenance(`run.json` 또는 `run_provenance_*.json`)의 `/seed` 에서 읽었습니다 [실행].
- FZP sha256 은 FZP 를 다시 읽지 않고, 기존 캐시가 그 경로를 스캔할 때 적은 값을 경로로 맞춰 옮겼습니다. "일치(n)" = 캐시 n 개의 값이 모두 같음. 크기·수정 시각은 이번에 읽은 값입니다 [실행].
- 열지 않은 것: `sealed`, 봉인 시드 37/59/61/67 이름, v3c3-s47·s53 캐시(`nc_s47.json`·`nc_s53.json`), `raw/historical_vsl_s43`(범위 밖) [실행 이름 거르기].
- 줄임: SP = scratchpad/k8, H = `D:/VISSIM_handoff/20261024`.

## 1. 팔 × 시드 (런 파일)

| 팔 | 망 | seed (provenance) | provenance sha256 | FZP (bytes, 수정 KST) | FZP sha256 (캐시) | inpx sha256 | 결정 폴더 action CSV 수 · 목록 sha256 | signal_readback.csv sha256 | 미터 LDP 수 |
|---|---|---|---|---|---|---|---|---|---|
| NC3 | v3c3 | 31 | `dd13998acf567d5a…` | `D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp` (1139192826, 2026-10-01 12:06:56) | 일치(6 캐시) `f8476f83e2c70821f00e96ece09a08aeb98eb553363aa65501ed7e47bb12e52e` | `3de889f0257d998b…` | - | - | 0 |
| V-A | v3c3 | 31 | `3ca00ac409fb6dfa…` | `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp` (1113724377, 2026-10-23 22:28:04) | 일치(8 캐시) `d3a440aff8db8ee50175b9cc9c4f0f091eee0fe4a0f90d53f11b72c63d67f88e` | `3de889f0257d998b…` | 61 · `b6fb9dd33aa1bd6a…` | `b76bc2d8f2c935b6…` | 0 |
| B | v3c3 | 31 | `88ae94165421ebd8…` | `D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_001.fzp` (1122662375, 2026-10-27 00:07:48) | 일치(4 캐시) `5932e6e195bae4ee567020ebbe3b539c93793347c98b1a35697037122b1fe52f` | `3de889f0257d998b…` | 61 · `e502eb0655dfe0d4…` | `670e1d79cf0e9d5d…` | 0 |
| VSL | v3c3 | 31 | `36a01b2241ab5afe…` | `D:/VISSIM_runs/20261027_vsl_v3c3/s31/run/vissim_eval/baseline_s31_v3c3vsl_001.fzp` (1149552072, 2026-10-27 12:36:52) | 일치(3 캐시) `63a827fe47606bee0ae17fd2eefaff01067c54e9024436dd7a4d6e12ce9eea54` | `046303541667838f…` | - | - | 8 |
| NC3 | v3c3 | 41 | `69910870bbdff8dd…` | `D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/vissim_eval/baseline_s41_v3c3nc_001.fzp` (1196651038, 2026-10-01 12:11:35) | 일치(6 캐시) `f63f00807b27d692c11296ddd5700cd233a8af2915cb51db3909c53e4e26f546` | `726af589bddb8c72…` | - | - | 0 |
| V-A | v3c3 | 41 | `cf46b5483c989288…` | `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp` (1145992810, 2026-10-23 22:53:57) | 일치(8 캐시) `eeea360784a1a9148c0349a45f4ee95a54c1e5c831d110218a5e8a4d398645c2` | `3de889f0257d998b…` | 61 · `1c8c453278addefa…` | `e2f1bd2ac3eeee3b…` | 0 |
| B | v3c3 | 41 | `276477312820187a…` | `D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s41_001.fzp` (1126938207, 2026-10-27 00:17:50) | 일치(4 캐시) `8ac58a253c6a5d87569dd9bf047be0cef743724153c240c178a097f962d4b159` | `3de889f0257d998b…` | 61 · `b076e54ce2a864e3…` | `5a21a3cb7ff0446e…` | 0 |
| VSL | v3c3 | 41 | `66de3c894e4b14b5…` | `D:/VISSIM_runs/20261027_vsl_v3c3/s41/run/vissim_eval/baseline_s41_v3c3vsl_001.fzp` (1178158159, 2026-10-27 12:38:59) | 일치(3 캐시) `ea91826e675e899bfbc889a713cc7400a1d75a6d4292bc5305a2f494a4d78177` | `e4953eaf8c8f983f…` | - | - | 8 |
| NC3 | v3c3 | 43 | `9ae8f15d02b2ab0d…` | `D:/VISSIM_runs/20261001_v3c3/s43_v3c3nc/run/vissim_eval/baseline_s43_v3c3nc_001.fzp` (1170017664, 2026-10-01 12:10:03) | 일치(6 캐시) `048823b966f60a662872a14d1a2ec126a662fe0c51f9d7e3105dbf8c0f7863e0` | `51478c397b3a2570…` | - | - | 0 |
| V-A | v3c3 | 43 | `bd9cac6e29c61d52…` | `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp` (1132495717, 2026-10-24 07:31:57) | 일치(8 캐시) `a38437a45019fee5408acb6d22a9401b3dfa50e43e3f7ae9c4ece4019b9ad8ae` | `3de889f0257d998b…` | 61 · `2616f95697aa413a…` | `5f15065244db567b…` | 0 |
| B | v3c3 | 43 | `36570a2bf6da0445…` | `D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_001.fzp` (1141723119, 2026-10-27 00:21:37) | 일치(4 캐시) `2f7011a33ef6d5004c2b7a2dcfa951e9649bc2bd95fec33cc51d762222755514` | `3de889f0257d998b…` | 61 · `47a4cc7a19e336c0…` | `e6ec1ab2af442b89…` | 0 |
| VSL | v3c3 | 43 | `fe668539b572d7eb…` | `D:/VISSIM_runs/20261027_vsl_v3c3/s43/run/vissim_eval/baseline_s43_v3c3vsl_001.fzp` (1162376857, 2026-10-27 12:39:02) | 일치(3 캐시) `5492358d78386b8bea1c32ea884bf6c073068b5205127ad4e4a7fa661387a3c8` | `94318d4d1c235fa8…` | - | - | 8 |
| J1(참고) | v3c3 | 31 | `195c1633c4a5ad36…` | `D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1r_s31_001.fzp` (1185574113, 2026-10-15 11:49:09) | 일치(4 캐시) `80c03a8d993b6a797dc39fb86965a31ae6a8b696c7b0bd235e503cc899b917d2` | `3de889f0257d998b…` | 61 · `458e1d3841b79055…` | `d22c58bdd7553c7f…` | 0 |
| J1(참고) | v3c3 | 41 | `7ef6872f94bf9277…` | `D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1_s41_001.fzp` (1146678641, 2026-10-14 07:19:32) | 일치(4 캐시) `7785ab17a4b5eec9e00e5a3709a9d5b057f3b0bfa39e800720f7b4b68523a116` | `3de889f0257d998b…` | 61 · `f44653df3a2d9f99…` | `660b99f67a5b7a39…` | 0 |
| J1(참고) | v3c3 | 43 | `c72a5c4262694dd0…` | `D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1_s43_001.fzp` (1195893122, 2026-10-14 11:57:01) | 일치(4 캐시) `1d1b20e42732d1d750e8abef34864e6973c6c1c9a90f043fdf90ae49cd23bc94` | `3de889f0257d998b…` | 61 · `39d78b57ad632221…` | `b28fbe216fb6acb4…` | 0 |
| codex NC | 64cf | 29 | `ae9d805654003f82…` | `H/raw/nc/vissim_eval/sdmpc31_nc9000_s29_001.fzp` (1183824519, 2026-10-24 18:17:20) | 일치(1 캐시) `1eaad57ff402963488e71dfd4440b6a9b6149249a4334430e51660e97d81a4d0` | `-` | - | - | 8 |
| codex joint | 64cf | 29 | `40afc8223b79a6b6…` | `H/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp` (1046204345, 2026-10-24 18:19:08) | 일치(2 캐시) `c0aa41bbdfc1cee4ac5d9531d555e317fac9dd208da52c751d8c449e1d2f0ac6` | `64cf5f55fe9990f3…` | 55 · `718ed226cf424287…` | `3e907118b220d96e…` | 8 |
| codex window | 64cf | 29 | `0d2a0b0213ad6f70…` | `H/raw/window/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp` (1062023225, 2026-10-24 18:20:54) | 일치(2 캐시) `ce2742b7f6934dda970dd8d3045683303cb716a0bb7d55f836f39b24f697a6c1` | `64cf5f55fe9990f3…` | 55 · `3088a91635eb7434…` | `767aa82f8dc464ac…` | 8 |
| codex off | 64cf | 29 | `58ddc2f245a52335…` | `H/raw/off/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp` (1059895046, 2026-10-24 18:22:26) | 일치(2 캐시) `73a20cbb813152f0f79a7955c3fe68ee508bc32f365382a3ca0898245f8a63c9` | `64cf5f55fe9990f3…` | 55 · `bc0076e4b1c4b729…` | `66c57b1743e2f37c…` | 8 |
| codex freeway_only | 64cf | 29 | `9efb542b4a64402b…` | `H/raw/freeway_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp` (1153668686, 2026-10-24 18:22:51) | 일치(2 캐시) `05b45b03ed323ad67bef1271ebeb0a5df88a320cdd9a906fade801efa201cdc2` | `64cf5f55fe9990f3…` | 55 · `f7fe2eb8e134bdaf…` | `6f44c18f15ba59c8…` | 8 |
| codex urban_only | 64cf | 29 | `ce9522eb8b6e155c…` | `H/raw/urban_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp` (1142359754, 2026-10-24 18:23:24) | 일치(1 캐시) `a8a4b4e2a681be36f0c89e908f6f13e837a75eb60870d887256c5935e4ca5b38` | `64cf5f55fe9990f3…` | 55 · `ac844f67bf50617c…` | `1717f4d30ffb7a85…` | 8 |
| A1 | 64cf | 29 | `4b56a69acc5c94cc…` | `D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp` (1044999452, 2026-10-26 09:25:50) | 일치(1 캐시) `9bf7c8c6f56099fb295cd5451377869fe9c73c0c725324ede74c4f3b7a31b6fb` | `64cf5f55fe9990f3…` | 55 · `f3eca30d15cdd683…` | `fddfb72ad1812263…` | 8 |
| LNC | 64cf | 29 | `8a849e87847c0f87…` | `D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp` (1183824515, 2026-09-24 23:21:11) | 일치(5 캐시) `9c097cc7e1f2840aea1cc61520a6302aa417b2925f33890fcde24c432e301f8b` | `-` | - | - | 8 |
| vsl_repro vsl | 64cf | 29 | `7b387e1d5e84bbd3…` | `D:/VISSIM_runs/vsl_repro_s29/vsl/run/vissim_eval/vsl_seed29_vsl_001.fzp` (1163737191, 2026-09-24 23:18:09) | 일치(2 캐시) `c874323fef14500d2232e314d512d3a745c35cecee9c9b253b8f25dfe5237200` | `-` | - | - | 8 |
| historical_alinea_s29/rm | 64cf | 29 | `bdc5d41e29dd6377…` | `H/raw/historical_alinea_s29/rm/run/vissim_eval/mtfc_s29_rm_001.fzp` (1227145689, 2026-10-24 18:23:44) | 없음 `-` | `-` | - | - | 8 |
| historical_alinea_s29/both | 64cf | 29 | `67121dc48d928961…` | `H/raw/historical_alinea_s29/both/run/vissim_eval/mtfc_s29_both_001.fzp` (1175952908, 2026-10-24 18:23:32) | 없음 `-` | `-` | - | - | 8 |
| historical_vsl_s29/none | 64cf | 29 | `dbf8dda606ab4a33…` | `H/raw/historical_vsl_s29/none/run/vissim_eval/mtfc_s29_none_001.fzp` (1183824530, 2026-10-24 18:23:55) | 없음 `-` | `-` | - | - | 8 |
| historical_vsl_s29/bottleneck90 | 64cf | 29 | `f68a29421e6103f1…` | `H/raw/historical_vsl_s29/bottleneck90/run/vissim_eval/mtfc_s29_bottleneck90_001.fzp` (1163737224, 2026-10-24 18:23:50) | 없음 `-` | `-` | - | - | 8 |

## 2. 기존 캐시 (팔별, 경로로 맞춤)

| 팔 | seed | 캐시 종류 | 파일 | 파일 sha256 |
|---|---|---|---|---|
| NC3 | 31 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_nc3_s31.json` | `4f156b104864adca85b0d44085630a415fc1075b8107e945c74f38020c18fb41` |
| NC3 | 31 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_nc3_s31.json` | `e1da8eb8573cb5ad71115207f603e8dc17b8fc53533fe7fe8f5fd857cd56435d` |
| NC3 | 31 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/nc_s31.json` | `352bddd3a28671575b7671ef1f013c816aa1c163ebd77bd320f452306abe00db` |
| NC3 | 31 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/nc3_s31.npz` | `fab9750ae47b748cea61c0efd22502fe685fbd409321851d3ea361fc954cffb5` |
| NC3 | 31 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/nc3_s31.npz` | `fab9750ae47b748cea61c0efd22502fe685fbd409321851d3ea361fc954cffb5` |
| NC3 | 31 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/nc3_s31.json` | `160e619d5831f105f4b8b15224b57ab7bf1ab3f56f7d3af4810e98fae540f54a` |
| NC3 | 31 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/nc3_s31.json` | `f3fe787cda213504c203bfe66bca2289436e6067e046c59d5095a656905db62d` |
| NC3 | 31 | vsl_cell(셀 31칸·차로 60s, 체인 6000-8600) | `SP/vsl_v3c3/out/cell/nc3_s31.json` | `6345ce9450062e6f961bb6622628491bddfe881dea1c945337ce9c2258dddb53` |
| NC3 | 31 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/nc31.json` | `1d30780a7cd027a88f897cd4f5bf43821c800a0bba01943b436e11a3198e2f0d` |
| V-A | 31 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_va_s31.json` | `b149f971f218def642a035c48403028bd41865abb3785d8e13083d390bd6000e` |
| V-A | 31 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_va_s31.json` | `ec8d62954cf39962bee3158014c8e4960597c73f7d22b69d76b8260ffd5d4c90` |
| V-A | 31 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/va_s31.json` | `d6f693aeaa6deb6784b955f547ff9f64fe9d429c6996af2fb6eada83c68f95a5` |
| V-A | 31 | o4_merge(10681 등 합류·연결로 재고) | `SP/rmcause/o1o4/fzp/va_s31.json` | `c6989d368a1e243c7729bb64e67f260d04659e859f2ed12dc7c236bb8d7e011a` |
| V-A | 31 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/va_s31.npz` | `c1484d0830644b0d2e39e1a9d67f54ab210450f51df2adcbcc9b4315c071c2e6` |
| V-A | 31 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/va_s31.npz` | `c1484d0830644b0d2e39e1a9d67f54ab210450f51df2adcbcc9b4315c071c2e6` |
| V-A | 31 | rb_cycles(미터별 10s 주기 GREEN 초 readback) | `SP/c_port/readback/out/cycles_va31.csv` | `349ea4ca9e2e786aa6c2956d1d111ded545be3a838bc4576cab00fff4b2ad07f` |
| V-A | 31 | rb_meter_scan(미터 헤드 통과·프레임) | `SP/c_port/readback/out/scan_va31.json` | `9929dbbf130e22162c760b3e2c4dd02e5085ebaaae029db2ecac99861040b97c` |
| V-A | 31 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/va_s31.json` | `8ff35536ced8cd9203dcdc4e1438d23e0d757295393f515f6bc0af56722b1e4e` |
| V-A | 31 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/va_s31.json` | `4f41f5fa53e159fc59dca76e67eac7c632b9bfe39873cb0ee7dcc773a0c3e237` |
| V-A | 31 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/va31.json` | `c4ac6341753a9518f49263b3454effdf6c7fa5ffb6d73395a2899b8ecf76360e` |
| B | 31 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_j1_s31.json` | `52a9164dba2ebaaa6a4deeaffcfed2c9144bae8a73f9f3c9d0bebc2f3a8b4960` |
| B | 31 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/j1_s31.npz` | `a2e049e3aca43bf8569462f09370cde1a7733fcb68a802a153ff59ab829d41ca` |
| B | 31 | rb_cycles(미터별 10s 주기 GREEN 초 readback) | `SP/c_port/readback/out/cycles_b31.csv` | `baff504fae3710af67c07f7421a13395f914820e6d8bec5762ae2c8b2b713be7` |
| B | 31 | rb_meter_scan(미터 헤드 통과·프레임) | `SP/c_port/readback/out/scan_b31.json` | `c7d6961b65e030056b76a6d5ce7c5f3beb986964bf972aff47c6ef40b9923847` |
| B | 31 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/j1_s31.json` | `4d5e94b0037f60d257a20d181c7a1c156bbf2bebf49b284fa81f99bcdad87838` |
| B | 31 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/b31.json` | `dbc5021101383f0eb511c87e4f20fc759a587e93ca36746a117e5a369a67eab1` |
| VSL | 31 | first_seen(입력별 첫 관측 누적) | `SP/vsl_v3c3/out/vhr/first_vsl_s31.json` | `0335b111527e298bb380d3ae740edfc0ab56ac35b052f2e4dbb2f602074a0fa2` |
| VSL | 31 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/vsl_v3c3/out/phys/vsl_s31.json` | `3169172b88d4c2b4515d8840ade32e1933a2c061f98dd60d18689bb032bbdc40` |
| VSL | 31 | vhr_link_integrals(링크별 적분 4꼴) | `SP/vsl_v3c3/out/vhr/vsl_s31.json` | `64112bf39ef8c7042a2cc37b089aab4dfb216ba4421c458e83abfe33366439a7` |
| VSL | 31 | vsl_cell(셀 31칸·차로 60s, 체인 6000-8600) | `SP/vsl_v3c3/out/cell/vsl_s31.json` | `1281f05cc19cbef14c67377db0aa119e412e574b10adb576c2be10a1236da24b` |
| NC3 | 41 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_nc3_s41.json` | `31cae96d667e5a1987c52b4ef7b0c9e070cf120fce838a8cf834a1f437cca249` |
| NC3 | 41 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_nc3_s41.json` | `976312123967429592aba33c2430fdd2387e9b92da5815b109544bbc8f30a521` |
| NC3 | 41 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/nc_s41.json` | `65051df07d65bbde5a287dc959481b2043a3e70f93104aad5b862dd32d811cd4` |
| NC3 | 41 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/nc3_s41.npz` | `79f585a9fcb97f227d506ef2d68f955d6155ddfad8a180ff6f4f1fb119401f88` |
| NC3 | 41 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/nc3_s41.npz` | `79f585a9fcb97f227d506ef2d68f955d6155ddfad8a180ff6f4f1fb119401f88` |
| NC3 | 41 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/nc3_s41.json` | `4983b9b4f8099b1b722d3bbd0e2f83dbefa12b0901b7265939ac175c1b900e68` |
| NC3 | 41 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/nc3_s41.json` | `1ae351a866612dac5bb4b7b6d1c60ed13bd88b7a27760ba4017805952fe52a47` |
| NC3 | 41 | vsl_cell(셀 31칸·차로 60s, 체인 6000-8600) | `SP/vsl_v3c3/out/cell/nc3_s41.json` | `70ef1f26ab17b413b497281e6f051aaf23d88d2c828e198a5b093db10623038e` |
| NC3 | 41 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/nc41.json` | `b14a1f923aae6eb73170cf49c363e4a63819fc0301fc766c0826a5ba1bcaa373` |
| V-A | 41 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_va_s41.json` | `da92234d73b7dc3a403caaecac453f9a4b1a8ff51b8c002ee6cca53dfd334c55` |
| V-A | 41 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_va_s41.json` | `73215ae37ed4a625d71a2779b6803814c6ad0ccb79ab613e6f7b6745ec848565` |
| V-A | 41 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/va_s41.json` | `b2782698f83435e4ce7a0f7e601f2b749694df079b6be68b36d7fcf1ae633c1a` |
| V-A | 41 | o4_merge(10681 등 합류·연결로 재고) | `SP/rmcause/o1o4/fzp/va_s41.json` | `e635110b28beb635327df6ae5d0d16ca39b501ef02d438f1cd1207abdb638083` |
| V-A | 41 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/va_s41.npz` | `5cdd66b53cf16f6a632483a43e3e5508bec7eff8e8343c2ea0df68222ee44b84` |
| V-A | 41 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/va_s41.npz` | `5cdd66b53cf16f6a632483a43e3e5508bec7eff8e8343c2ea0df68222ee44b84` |
| V-A | 41 | rb_cycles(미터별 10s 주기 GREEN 초 readback) | `SP/c_port/readback/out/cycles_va41.csv` | `aa22b0ff82c482663e7812d44e553e7b1abfd5b3f0a322db0ad5dfdb9b78fee9` |
| V-A | 41 | rb_meter_scan(미터 헤드 통과·프레임) | `SP/c_port/readback/out/scan_va41.json` | `b7f9505967061f7022d6e6ee97a51400d46d7ce93c5b7534bfea60905b5a1c50` |
| V-A | 41 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/va_s41.json` | `d888823d98ab18af0dac311432371fa9ef34a16039590a7505f08b1b9d940d6b` |
| V-A | 41 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/va_s41.json` | `6eb1dd0aa24951a2275cad998778d1dbe40b26024831ccb21163e3ba1a4ddd80` |
| V-A | 41 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/va41.json` | `f8c9bdc79b5fbe13cb5a61739113964f27b43fb50e85460dbad10eaeba9fbfad` |
| B | 41 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_j1_s41.json` | `298979aa7ded01195f3d2c99029292f889e9b48b801167dd1a172efd33631517` |
| B | 41 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/j1_s41.npz` | `55be063d02163570ee36471f1cf5ef05da8301fd9679429f6b3a905daabd4c5d` |
| B | 41 | rb_cycles(미터별 10s 주기 GREEN 초 readback) | `SP/c_port/readback/out/cycles_b41.csv` | `6d9d9da5dcd2a9d591fa5425ea9b15bca71b2c9e5e616a1dd8e87a499f974e88` |
| B | 41 | rb_meter_scan(미터 헤드 통과·프레임) | `SP/c_port/readback/out/scan_b41.json` | `32055e50c08060170e4b6e797d409a828cd0ddb7b85170913dfa37066ecb15df` |
| B | 41 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/j1_s41.json` | `9a4d7cd3cb9e14db8868dac86acfc3fb9b0129052b0d78e9815843fdc3ff5baf` |
| B | 41 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/b41.json` | `670a08313f2bf54f624ea45a31460c1229fa1e042da9021bedc0e7b440d0dbb0` |
| VSL | 41 | first_seen(입력별 첫 관측 누적) | `SP/vsl_v3c3/out/vhr/first_vsl_s41.json` | `e8d956c97114c2a26682e801f6ae3e34a6b6641d79c743ac55acb3fc86fc4c78` |
| VSL | 41 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/vsl_v3c3/out/phys/vsl_s41.json` | `c9fd195a637ccaec33a7e0e8a0cd89dea052d52e55fdaa52f55486140de09cc0` |
| VSL | 41 | vhr_link_integrals(링크별 적분 4꼴) | `SP/vsl_v3c3/out/vhr/vsl_s41.json` | `6fb9e514207e223047f0a9a06608ef077dc92f6a064f76707fe1e0ad09af0f64` |
| VSL | 41 | vsl_cell(셀 31칸·차로 60s, 체인 6000-8600) | `SP/vsl_v3c3/out/cell/vsl_s41.json` | `4e6a8161fa9c8ee8f3660c24aae4b6797ee01879037cd0c01c54bc31b8bd0542` |
| NC3 | 43 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_nc3_s43.json` | `86cca5621e988f777f5da05b4ff1109dadbb6973793dfc3943db9d6d22899d57` |
| NC3 | 43 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_nc3_s43.json` | `ebcf0b5b2aeff843c3911744c9d29b9311970e16f9f475074c4c52e86fbc8369` |
| NC3 | 43 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/nc_s43.json` | `7afd43e8ed482fa60ae5cf5736f4b6e38b07f9844fc3737ec22f372441b2a843` |
| NC3 | 43 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/nc3_s43.npz` | `6561582748d506ad725fce24e231c17dbadd29620a5656af262d4718b0ef2436` |
| NC3 | 43 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/nc3_s43.npz` | `6561582748d506ad725fce24e231c17dbadd29620a5656af262d4718b0ef2436` |
| NC3 | 43 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/nc3_s43.json` | `8725a1c66171675124425b4db6ec9ad4b2ebdcdc16dfbbd03a490006d4156048` |
| NC3 | 43 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/nc3_s43.json` | `fb90d49b5b95349c25bd1feddf65fbbd71bfcb28861467339284935ae795a793` |
| NC3 | 43 | vsl_cell(셀 31칸·차로 60s, 체인 6000-8600) | `SP/vsl_v3c3/out/cell/nc3_s43.json` | `a67a8751bcfa841c2d69e823523ea19bff39179ae384de8ae60fed3cb0e83abd` |
| NC3 | 43 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/nc43.json` | `eb2a597d0679e42ed29478f45b797e73e8678be2318c19713a1fbf5914f383de` |
| V-A | 43 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_va_s43.json` | `6b7686fa1ddc15188711490abef89caeb4e1d07b84d1eee759e9ef070f5cde81` |
| V-A | 43 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_va_s43.json` | `48f584773c418914e8f16a623e1bce4a33760eb95f98917e22f295ad40698fcd` |
| V-A | 43 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/va_s43.json` | `9035a75c7efc5ab8d02eaefa92c7b1ced5a4923757b85a600af128b34ccba23c` |
| V-A | 43 | o4_merge(10681 등 합류·연결로 재고) | `SP/rmcause/o1o4/fzp/va_s43.json` | `ae95629524289f4c369d392f051296f06fa785dc3f2d38b9fa5aea19d54ce22a` |
| V-A | 43 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/va_s43.npz` | `9b27843cdfaea5c657ab8ef467838c538fd46b5c70803798d2badb19645c0c20` |
| V-A | 43 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/va_s43.npz` | `9b27843cdfaea5c657ab8ef467838c538fd46b5c70803798d2badb19645c0c20` |
| V-A | 43 | rb_cycles(미터별 10s 주기 GREEN 초 readback) | `SP/c_port/readback/out/cycles_va43.csv` | `0549d85a3440d5d5053e87e0d755c566f7f41de768d31637a5a1dcdb3c80e0e6` |
| V-A | 43 | rb_meter_scan(미터 헤드 통과·프레임) | `SP/c_port/readback/out/scan_va43.json` | `71d3b59bd7a1550cdd7c699d33a5d0a7930457b0ab319c48a57bc267f0c288a1` |
| V-A | 43 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/va_s43.json` | `0c84c10284faf97811e93377914dcb8bd81cdec83b427e0f592f047a948bca1b` |
| V-A | 43 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/va_s43.json` | `561b673e3b851f4cd76a9add4fe221b590ac870d5d76cfec544da738425e5a4f` |
| V-A | 43 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/va43.json` | `70d99a46c9300152b4babb532dfee765a7a2f6c22f6708c93fe540b525df45aa` |
| B | 43 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr_b/scan_out/first_j1_s43.json` | `cc16b867943a35cfda8af7d30185145bb9e9eada651bfa3b4cf1d4c41f846cca` |
| B | 43 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/j1_s43.npz` | `9788729638513862db788daadaa31f1aaddea8d5394d4e1a0cb98c0e0493002e` |
| B | 43 | rb_cycles(미터별 10s 주기 GREEN 초 readback) | `SP/c_port/readback/out/cycles_b43.csv` | `2439f754844ee3efca4d66c999f564d5f5d4398e884f8c5a823a72b5d92b7593` |
| B | 43 | rb_meter_scan(미터 헤드 통과·프레임) | `SP/c_port/readback/out/scan_b43.json` | `6ca4877952110cb9400c1d57e6d7b30da1bb4de8d046da46339857af98644a3b` |
| B | 43 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr_b/scan_out/j1_s43.json` | `93253733953a033f2c7c84bfcda051b93d7e1c1e0a3ac974e4134d33f9771b15` |
| B | 43 | w1099(FW_W 입구 26·120·129 칸) | `SP/c_port/w1099/out/b43.json` | `bf5ddb439484f3a543c4d7446bdc841037301d61678a89f275fe113d4d6740c9` |
| VSL | 43 | first_seen(입력별 첫 관측 누적) | `SP/vsl_v3c3/out/vhr/first_vsl_s43.json` | `bd7648669eb36d546d0fa6146f292ea2e06ad134f9c354400378748031e69cfa` |
| VSL | 43 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/vsl_v3c3/out/phys/vsl_s43.json` | `61526d641f9bf888e159a72642908d3e184c06c931561a2f172036265e0a5200` |
| VSL | 43 | vhr_link_integrals(링크별 적분 4꼴) | `SP/vsl_v3c3/out/vhr/vsl_s43.json` | `b0cf5b9f532164f9c5187bae81991102957068277c7d23f986402e0c5f64e434` |
| VSL | 43 | vsl_cell(셀 31칸·차로 60s, 체인 6000-8600) | `SP/vsl_v3c3/out/cell/vsl_s43.json` | `3b760d041f1aec9d2ef30acb78751a81184cf3ded2a2c7928476333c1c56cc38` |
| J1(참고) | 31 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_j1_s31.json` | `3a5198ed403747d860a23c2345ac62ad1ee672808a8c152db59914ef44d69d63` |
| J1(참고) | 31 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/j1_s31.json` | `d9dcff28a59eb150a238bfb1ede70acb318d79c2f7eb531a95245c1385084820` |
| J1(참고) | 31 | o4_merge(10681 등 합류·연결로 재고) | `SP/rmcause/o1o4/fzp/j1_s31r.json` | `55047a762a4b35aa00e94f098532a6974684b6f40019fc8ff6fa432037721295` |
| J1(참고) | 31 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/j1_s31.npz` | `003b02ef5344ec2ec5866a46edb0163617ac9380e9d22f74b0b3de2c1164d3dc` |
| J1(참고) | 31 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/j1_s31.json` | `15edf17322cb6072e668fd07582c01f0b301f07dea085e150a372afce1f92741` |
| J1(참고) | 41 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_j1_s41.json` | `5f722d9bf5ee7963a23a79a898ff7aa6a3c927688cef05aea86b9ff4d9731288` |
| J1(참고) | 41 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/j1_s41.json` | `d8ce1fe121079eb1ed9efe53fa6cb7a633cd605edf0d3e78f40085bc12490fed` |
| J1(참고) | 41 | o4_merge(10681 등 합류·연결로 재고) | `SP/rmcause/o1o4/fzp/j1_s41.json` | `314dc1edfd3fa236d28252604e99a438d6175209a9b76bcf319030405c4e6c20` |
| J1(참고) | 41 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/j1_s41.npz` | `c4d66e2865bfdea668ecbe5aa6825212fb51a186872c3a8bc4b0a65e7fbd3768` |
| J1(참고) | 41 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/j1_s41.json` | `92a0b9d91f0d89791cc82a81db6d5ade4fc56cf9336459d685b7a730a873191c` |
| J1(참고) | 43 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_j1_s43.json` | `10369236b2f2dd7cf202b69ea7b6e7a3cb15111f94ab6a358e61f2299d58c332` |
| J1(참고) | 43 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/j1_s43.json` | `7af1f1444e3f20b1c7d6b85e3edfc7f971e6ad87d3beded4d781a540834c97a0` |
| J1(참고) | 43 | o4_merge(10681 등 합류·연결로 재고) | `SP/rmcause/o1o4/fzp/j1_s43.json` | `198dd7197bcc40ae27dd065899c6d61533c842b6af7a81f8cf7d31adf0707478` |
| J1(참고) | 43 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/j1_s43.npz` | `194312ac9cce531a517aea8b0fa44026c0cab8719aae5f9c014bee8e520b8abb` |
| J1(참고) | 43 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/j1_s43.json` | `c32b2c391974b0da78274020c84bb5838e990c235171be6b74bbe972809754ae` |
| codex NC | 29 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_nc_raw.json` | `2a1ea7fa303a69d294d234cdc4368dba75158cfb29a1fc3af761241a14735b45` |
| codex NC | 29 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/nc_raw.json` | `c5d5eaae592b64641bbaa767fd94c0bf098b5311113790d357471a7782f0d5c8` |
| codex joint | 29 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_joint.json` | `259552528126b94625f5e877f70c1ed35d91811afbfa7313628a2510a496dfa7` |
| codex joint | 29 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/c_port/vsl/out/scan/cx_joint_s29.json` | `c2d2b8dc7a36315d4307429ebc3f931b746d958e4586eeb42071a87be2de8bb3` |
| codex joint | 29 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/joint.json` | `771c0ffeb21cd037ffe075588387d673f6659789a12edd5b638847417e904f25` |
| codex window | 29 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_window.json` | `e59c298b22881e0d3738af3a03e614cad3c951032fecfb9e6feab75107f0acad` |
| codex window | 29 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/c_port/vsl/out/scan/cx_window_s29.json` | `a7d8a926f6af679472a8cd2017b14e4fce95245be1454530511984bcacd0ea68` |
| codex window | 29 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/window.json` | `ae3558f6aabed0a7446432d21872b3885f02ea17a0e3e34812f710de35f7b266` |
| codex off | 29 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/vhr/scan_out/first_off.json` | `c7b20fc4548bfc4f03f6c6a4c84ec2ea8077e42edb6bacba01d51535669c831a` |
| codex off | 29 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/c_port/vsl/out/scan/cx_off_s29.json` | `d13da72e196fb270c807241e8cd41ea4b5ce932b8e80cdaaa13bb9bde85e0e2b` |
| codex off | 29 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/off.json` | `a4407838e90d965e5e2e4cfa9b008b9f64561ba70c73b3532ac6e090f2ee0599` |
| codex freeway_only | 29 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/c_port/vsl/out/scan/cx_fwonly_s29.json` | `f01c1f65eb5c650c447f697701b1c628e777716d606ddbc441374d917a5fe342` |
| codex freeway_only | 29 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/freeway_only.json` | `b3eb447174aca51c5a07e026d17952f07e14c46afc389cbbf5e063493f41ec3a` |
| codex urban_only | 29 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/urban_only.json` | `23278f7302436af775ab681b62abbb7273d73113902c94f7b40aaee51ea40564` |
| A1 | 29 | a1_link_residence(링크별 0-8100 적분) | `SP/codex_handoff/work/a1/full/scan/a1.json` | `e0d475a667e8ada8353bdb24a9215d81de68a78f413c0bd6b73277e362701690` |
| A1 | 29 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/a1/full/firstseen/first_a1.json` | `fc1fb0253f643e8258969a89751468f3e58e17e037678e01b6a613876e14e3fc` |
| A1 | 29 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/c_port/vsl/out/scan/a1_s29.json` | `5f996c93076b439e026edf3e37d60c5279df88bd0cc585f68d620b3c2b357ad4` |
| LNC | 29 | first_seen(입력별 첫 관측 누적) | `SP/codex_handoff/work/a1/full/firstseen/first_lnc.json` | `8eefa931a343ab3918966834ca9c48f6cd8a6c03b455e8572856313e944f57ce` |
| LNC | 29 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/phys/scan/cf_s29_none.json` | `d5113843de6fe23f630e06bf820ad6fb39f66d534192c5a6c1601e045eed133c` |
| LNC | 29 | linkbin(링크×150s 재고·대기·삽입) | `SP/rmcause/o1o4/scan/lb_nc_s29.json` | `bc30ba31d693306014b276807be13a73fd4a4d740fee84a45c020d6d17a41ddd` |
| LNC | 29 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega/cache/lnc_64cf_s29.npz` | `64cb0aef33a439ea806071ce8ecf5cd9bdfc5750f8d7fdc2cbfde3748edeef1f` |
| LNC | 29 | omega_npz(링크×5s 프레임 재고) | `SP/codex_handoff/work/omega_b/cache/lnc_64cf_s29.npz` | `64cb0aef33a439ea806071ce8ecf5cd9bdfc5750f8d7fdc2cbfde3748edeef1f` |
| LNC | 29 | vhr_link_integrals(링크별 적분 4꼴) | `SP/codex_handoff/work/vhr/scan_out/lnc.json` | `0f666f4f952f2f15d826e2cf46af2ab67d09de68345477846b2532b72ce9683f` |
| vsl_repro vsl | 29 | first_seen(입력별 첫 관측 누적) | `SP/c_port/vsl/out/first_vsl.json` | `ceb5f188fd41090e8288d5d07dcd89d1050cc38c5afc6459229f9b670a91bc77` |
| vsl_repro vsl | 29 | fwe_scan(FW_E 체인 100m×60s·차로·램프 60s) | `SP/rmcause/o1o4/scan/vsl_s29.json` | `89793cf05fc3e52aa3381606dce2baa40f66ddef5306536ded651bb6c982d471` |
| vsl_repro vsl | 29 | linkbin(링크×150s 재고·대기·삽입) | `SP/rmcause/o1o4/scan/lb_vsl_s29.json` | `96220220eea4fa4ec51460d605fd53537de83f10061a77e743c55b897259dec4` |

- 경로가 이 표의 런과 맞지 않은 캐시: `SP/rmcause/o1o4/scan/lb_w264_s29.json` (D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s29_001.fzp); `SP/rmcause/o1o4/scan/w264_s29.json` (D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s29_001.fzp)

## 3. 기존 도구·정의·문서·결과 표 sha256 (`out/pins_existing.json`, `out/pins_existing.sha256`)

### tool

| 파일 | bytes | sha256 |
|---|---:|---|
| `SP/rmcause/phys/fwe_scan.py` | 7862 | `0619e9fcbe14fd1b2e53d1cf884a8d740c0542f5686df33ef26f450a2b08bae7` |
| `SP/rmcause/phys/fwe_analyze.py` | 8230 | `5c055dd44b0ae8be6ca4907186e0ba8f25afb8626c3adfc097a5135c918e3aaf` |
| `SP/rmcause/o1o4/work/tails.py` | 3325 | `cb6c0bd4407fbaad8b403ccc34fc2bcfb1f9b9af318a67ee963b120a8bfb5569` |
| `SP/rmcause/o1o4/work/linkbin_scan.py` | 3478 | `a22d5fa69aff12b5206041437613ad0b7a0decdf56cb5ec7d7e5a071d974b82b` |
| `SP/codex_handoff/work/vhr/vhr_firstseen.py` | 3353 | `42e17585172e8c3cdc529ee0b0768ec958ab34729bbe686c590e70053ada4c94` |
| `SP/codex_handoff/work/vhr/vhr_unins.py` | 2999 | `fc233013623d797657c19e0efbb59b6ccad720a19a84e723491ad73a34337532` |
| `SP/codex_handoff/work/vhr/vhr_scan.py` | 5867 | `a19942b8358b353329c30818c59b63cc88ff4b65e8b3dfa291de89e4c1de1865` |
| `SP/codex_handoff/work/vhr/vhr_v3c3_all.py` | 4735 | `b42372512a26960530cfe89b1dc731a74f7fc83531c17f4ec04c4706409d2c99` |
| `SP/codex_handoff/work/vhr_b/vhr_v3c3_all_b.py` | 4840 | `d91ded54904eb43a78a49f0d2a1382396258a0cf0621fbf6e7ba2410fb7283ed` |
| `SP/codex_handoff/work/omega/omega701_recount.py` | 29278 | `5b7826f65c58a883c2dc4a3eccd6de92563bb12f812dd0d6579be8a42c92a5ac` |
| `SP/codex_handoff/work/omega/check_fzp_copy.py` | 2551 | `1a2cf5681fc18c653328bb460c0af2519760a11fa4744c35d85a0f15e0506a19` |
| `SP/vsl_v3c3/tools/vsl_metrics.py` | 26790 | `160c23c76d354b769718ab31044782609b96e238196b2bf1817ef053aacca71c` |
| `SP/vsl_v3c3/tools/vsl_cell_scan.py` | 7524 | `fa5aeafd01c99297652f8f5fce6d5f760cdbb223640b3258d2020cd03229a078` |
| `SP/vsl_v3c3/tools/vsl_vhr.py` | 1929 | `52086b7c095f0164dace251f5a379d26e101b197a362348cf23a4648a7b85900` |
| `SP/codex_handoff/work/rawcheck/rm_exec.py` | 1592 | `27f6402205d6c7cbd3524a44ee35632e19a90f681a10d21fffa3b5518dbb1c10` |
| `SP/c_port/readback/tools/rb_readback.py` | 11840 | `cee5f2629b8accc602655cbcbf2dc706796f57b97a69f66ee25966ac550a96cb` |
| `SP/c_port/readback/tools/rb_fzp_scan.py` | 5782 | `3687d3c8609786f09045e1c50975b8e2c7c7dc2c91408b3e537ea31fdc7aec84` |
| `SP/c_port/readback/tools/rb_discharge.py` | 11241 | `4c385da965298b49e445ba599cdf0314f719184bee900ae78b309f9ecd4303e9` |
| `H/code/handoff/check_fzp.py` | 2551 | `1a2cf5681fc18c653328bb460c0af2519760a11fa4744c35d85a0f15e0506a19` |
| `H/analysis/original_scripts/solo355_compare_20261014.py` | 9814 | `7fc91d604214b3ea757c2e7c34f59a694a801ac21bf83c7e02fd57cde27e7fd1` |

### definition

| 파일 | bytes | sha256 |
|---|---:|---|
| `H/derived/omega_membership_exact.json` | 150198 | `efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473` |
| `H/derived/reporting_partition.json` | 46448 | `3142f69c0502f6d9d12416b5b6131d57799bf8f2d17d207b4b0312e854f1dd2b` |
| `H/derived/metrics_0_8100.csv` | 10485 | `a2757f7288ba3f0e0d91222c25d353c0f3f015af28e2f9ebdb594508e3cfc37a` |
| `H/derived/independent_fzp_counts.json` | 1965 | `f55be7114af7b1d9049e7daee9748e667491dd486a07c1e92b6bc0aa010e09b4` |
| `H/derived/decision_greens.csv` | 471457 | `5f63309329ab26f1a7269b77ac9f1c964bfb2115fbcd4b18a455ff87086792e0` |

### document

| 파일 | bytes | sha256 |
|---|---:|---|
| `SP/K9_1_J1_NOTES_20261013.md` | 70420 | `efc3a7220aa1d1b3c155f77662209accffba59cc54b155b8029b4ca5bf203558` |
| `SP/codex_handoff/HANDOFF_RESULTS.md` | 56211 | `964a23cea5548c997e199e0d800c6f259c0d24ca3cebf2a8250513108a18cbfa` |
| `SP/codex_handoff/B_RESULTS.md` | 44031 | `152a2f6fe0fd6c5cfd1462ba7d7e444cd13a6bd0ba2554874d07a1390a8209f9` |
| `SP/codex_handoff/B_RESULTS_ERRATA_20261027.md` | 1584 | `6276c4a7db90b25b87f231d8d70b74e49c7b100fee6423481406717f02c968fe` |
| `SP/codex_handoff/OMEGA701_V3C3.md` | 55924 | `5c02894a84ed155c428004e740e27bb074eba482a747fcea43db8f2314470c64` |
| `SP/codex_handoff/R_NET.md` | 33293 | `f1e15b749c62ed333e96df2cb69beee6acff82cd5808a09f3a07b83009bd1f46` |
| `SP/codex_handoff/a1/A1_RESULT.md` | 46951 | `0ef733fb2450c71925d6b2723c7446a7441d6bf5581a23d105d2523e095cc714` |
| `SP/c_port/READBACK_METER.md` | 21979 | `2fd9863934f93d09341e84df45f7c67cc404e0c4e97dcb85ed1ec465bbd7f980` |
| `SP/c_port/INPUT1099.md` | 39059 | `c89011d8d1d7b3a45fea46f2622d87930e6f0e361969e4dae219e418b6d54274` |
| `SP/c_port/VSL_OFFLINE.md` | 45437 | `a8ff255ecf5b20717c16b7c6bbb45e388810fa3d8bef47ef23e686a759a5d0ba` |
| `SP/vsl_v3c3/VSL_RESULTS.md` | 42537 | `9bbf83a3c320dd0f46c7f6ad40621b66b966ce7e40e8c587a695a22f105da86f` |
| `SP/vsl_v3c3/VSL_REPORT.md` | 61875 | `01bf8a3122f2b6d6080cfedfc2789eca297e87e4b2c76202ea81289aa8d235cf` |
| `SP/vsl_v3c3/PRE_VSL.md` | 33818 | `27452ae62ae84e7c1cbe4717f1c8777b3c18b5a3f5d18b7cd5da033d83a3faf1` |
| `SP/vsl_v3c3/o1o2/PRE_O1O2.md` | 10515 | `be6852a25b0662a3be5dbad3d72b1fb2f241aae2c1cd7ff8aca0f9f484932178` |
| `SP/rmcause/METER_CAUSE.md` | 56841 | `0b4036c62cd2e2983c9965dd6010a4c93a88d83635a98293e82acb3fe92c626c` |
| `SP/rmcause/o1o4/METER_NEXT.md` | 40793 | `5f3c5ce80ea79e9afb6356471fd68dd5ad1ddf3cce04bc5644e00fe901c74cfe` |
| `SP/rmcause/r2c_n/METER_NEXT2.md` | 39116 | `acebbe738677eebc1cbb36b9efca2d9e905bdc9b2bddc8d5b229563cbc43b33c` |
| `SP/rmcause/INV_PHYSICS.md` | 28882 | `00d94e900a67c5edbe91079e5fce4bcbf55035327c7ded9c3a548f47358574c9` |
| `SP/rmcause/o1o4/O4_MERGE_10681.md` | 35560 | `fb178ef4beee4354678098151aadc3aa3251205c128e375eec2c1c6c940b5407` |
| `SP/rmcause/o1o4/W264_READ.md` | 45628 | `8db20647d3174140ab145212fa7b6a8ed3d9ad2c64356d23fbf707ded0ad5a6e` |
| `SP/k92/va/analysis/VA_REPORT.md` | 104247 | `b57022e651adeefcaf1484993c20fd940b2e13012f0437e3a5b6c5ad6a20fc1b` |
| `SP/HANDOFF_codex_a49981ff.md` | 35428 | `e2cef38c99ad22dfcd575581cec35a40c7c66c4891e9dd57abf9d0458c605b56` |

### result_table

| 파일 | bytes | sha256 |
|---|---:|---|
| `SP/codex_handoff/work/omega/omega701_pairs.csv` | 27903 | `82c094d3cd0cb55e69bd56dcfdf32ee69a6a75ef7ad79ca315d52ce59cdd218c` |
| `SP/codex_handoff/work/omega/omega701_levels.csv` | 29275 | `f0a6d31d302ca3d69899a6971cf5c8ed32df09141a3fdf33caf4db26c8dbe207` |
| `SP/codex_handoff/work/omega/omega701_per_link.csv` | 1448577 | `cf785d2b40a5acc8305ea61aefab26db11d499f8c8354cc3bf2ec53b6beda296` |
| `SP/codex_handoff/work/omega/omega701_v3c3.json` | 280737 | `fa6d24cfdee49a9bb79884e1fdc07736ba01cbe4c7bf91fb746f0b69ecb173cc` |
| `SP/codex_handoff/work/omega_b/omega701_v3c3.json` | 275407 | `823f9dccf4fa211fc13e11c3081e6729ebe6f98a97ef127547bb5239b6064f2e` |
| `SP/codex_handoff/work/omega_b/omega701_per_link.csv` | 1448108 | `c4f7a3a3abc87d4834c48fb01b60d7fba76a2b9fc976a98b571a3f0715adac56` |
| `SP/codex_handoff/work/vhr/v3c3_all.json` | 50911 | `bf26275e3854e8f4bb0d0990a9d626d00c952a644595a1fa36caa54512a1d730` |
| `SP/codex_handoff/work/vhr_b/v3c3_all.json` | 51341 | `f982fbff497645c7155d53e9c272388e5136641f5bb9580bc8f3a8c606ba251a` |
| `SP/codex_handoff/work/vhr/unins_out.json` | 4286 | `1328eb0c28956c04cf33fb140d208a1f15cd5e1a42532601e480cc00492ea2cf` |
| `SP/vsl_v3c3/out/vsl_metrics.json` | 566850 | `b1eea2f19257ff0a24d7e819ba5de9e1cd3e11fecf7223a45230ec3579d7ecf2` |
| `SP/rmcause/phys/out_all.json` | 290762 | `08cc57c3ba9485830f024c65817a7fa65252e30daef3ff8ac7691ccc4906cdb1` |
| `SP/c_port/vsl/out/v2b.json` | 413089 | `e1745813d3aaeb0d1b0f4dcf1d99f3af958716cff4bb0ec940e79df5546b7d3e` |
| `SP/c_port/vsl/out/v4_omega.json` | 1605 | `de854edb731614f9f76504fb19cc83d1ad9e61021c2c9f31c02c74d8879d0bd0` |
| `SP/codex_handoff/work/a1/full/metrics_out_a1.json` | 14543 | `937c477051f998b91f62b376c4428155ba4d5ebe19c66742682c483d0d61d8e7` |
| `SP/c_port/readback/out/readback.json` | 64705 | `4804bdbc91d141a6322ed96b5a3bc79ad12d78178bba41781ff57984895614dc` |
| `SP/c_port/readback/out/discharge.json` | 2158260 | `34220b5c7fc30cbcba9fa0f2def206301f08212a9d2a62200ae1b7f021e90a3d` |

