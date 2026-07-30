# PORT_MANIFEST v3 — the transplant universe, partitioned by owner

All 144 files in the transplant universe, with blob sha256 at tag `legacy-v0.2`
(= `57cd833d742272b0af8f35801dfa7dfb9534c3e0`; resolve with `^{commit}`, D-028d). Committed and
**Provenance of this file, stated exactly** (plan-v8 finding 4): GMR-001 committed and froze the
**141-row v2 manifest**, and its approved verification was `141/141`. Rows **142-144 are added by
GMR-003R**, each re-verified against the tag in that PR — they were never part of GMR-001's
commit or its verdict. **Every row has exactly one owner**, so no file is claimed twice and none
can vanish between tickets (plan-v2 review, finding 2).

**v3 (D-039, D-040)** adds rows 142-144 — `docs/GLOSSARY.md`,
`docs/adr/0008-golden-testing-strategy.md`, and `docs/STREAMLIT_PROTOTYPE.md`. GMS-001 categorized all three REFERENCE; that was wrong,
and the GMR-003 diagnostic proved it empirically: five transplanted tests read these documents
and assert against their content, so they are **dependencies of ported tests, not reference
material**. With the first two present the affected modules go 4 failed + 17 skipped → 37 passed
and the suite's skip set becomes byte-identical to the tag's; with `docs/STREAMLIT_PROTOTYPE.md`
present, `test_deployment_documentation_names_the_entrypoint_and_requirements` passes — measured,
content-only assertions — which keeps the deployment-contract architecture guard live rather than
inert (plan-v8 finding 5). Their blob hashes come from the D-029 inventory and are unchanged by
this recategorization; none of the three perturbs node-ID collection, which scans `*.py`.

| Owner | Rows | Meaning |
| --- | --- | --- |
| `SUPERSEDED-000A` | 1 | `.gitignore` — replaced by the GMN-000A **authored** file, approved with its full text in the GMN-000A review. The legacy blob is deliberately NOT transplanted; its hash is recorded here so the difference is a documented ruling, not an omission. |
| `GMR-001` | 4 | Toolchain — transplanted with the enumerated deviations (name/version, ruff pin, `-e .`), so resulting hashes intentionally differ; the ticket's provenance table records legacy hash → result hash per file. |
| `GMR-002` | 1 | `ci.yml` — transplanted with zero deviations; resulting hash must equal the manifest hash. |
| `GMR-003` | 138 | The core. Zero deviations; resulting hash equals the manifest hash for every row. The empty `__init__.py` placeholders from the GMR-001 skeleton are **replaced** by these real files — that is the designed hand-off, not a conflict. |

**Verification, by review object** (plan-v9 finding 5 — one paragraph may not credit GMR-001 with
a verification it never performed): every row's hash is re-verified against the frozen tag in the
legacy clone — `git cat-file blob legacy-v0.2^{commit}:<path> | sha256sum` — grounding this
manifest against the repository rather than a document. **GMR-001 verified the 141 rows of v2 and
its approved evidence was `141/141`. GMR-003R verifies rows 142-144 and pastes the `144/144`
total.** GMR-003 then re-verifies its own 138 owned rows in its provenance table.

| # | Owner | Legacy path | Blob sha256 |
| --- | --- | --- | --- |
| 1 | GMR-003 | `src/greenmachine/__init__.py` | `2476a2dd0743f23a5e540acd638dd3c7959a0632f402306513f5da085c176554` |
| 2 | GMR-003 | `src/greenmachine/common/__init__.py` | `733508d7db9b01f7142517edc4478afc713b834420f497dd2d62d8494266509f` |
| 3 | GMR-003 | `src/greenmachine/common/clock.py` | `8aca0069fda53056f68e33be23d6346e17113f074247030153bd9eaf3f553e56` |
| 4 | GMR-003 | `src/greenmachine/common/errors.py` | `93c8f3eb3649799651fc6d3453359908a068840a056f3c2009eb68dce69b80d1` |
| 5 | GMR-003 | `src/greenmachine/common/ids.py` | `8e5c62fccb5205da3b19221e75cf0768b850d530db2a92f0d8d79da78feff16d` |
| 6 | GMR-003 | `src/greenmachine/common/logging.py` | `f2160fa2b11033a23b3f403a4d26d92885102dc1df265acbc267b884486cba37` |
| 7 | GMR-003 | `src/greenmachine/common/numeric.py` | `8e72c4bcd6f54fe781334583d47e3bbfeecf2af283dca5f89d7f0dcce845d4da` |
| 8 | GMR-003 | `src/greenmachine/common/serialization.py` | `a253d91ad2a93ddb97fccaa5ee424111f3ca13c0e19a39e857f13f59faf3088e` |
| 9 | GMR-003 | `src/greenmachine/config/__init__.py` | `56e14ac9050be12cc73506424bd03e005cc8482cfc8bf15c817cf2f17c95172c` |
| 10 | GMR-003 | `src/greenmachine/config/errors.py` | `3c9a27db041c4216355fae6092fc0e11a18ec63bb223029b422aace551b0b55d` |
| 11 | GMR-003 | `src/greenmachine/config/hashing.py` | `56b3bcdd1952861c255173e5f1c968bcd973b485d4590039917145b3363b4f22` |
| 12 | GMR-003 | `src/greenmachine/config/loader.py` | `eb9b1c1c69a5adfff51e1921999b6fe766548f2e1e13b0481bd955e3befbceed` |
| 13 | GMR-003 | `src/greenmachine/config/schema.py` | `a7ecae5143bb438c696863daa3dd0c3089d0dc4e2eb3285eba49776e7cd67415` |
| 14 | GMR-003 | `src/greenmachine/config/validation_rules.py` | `e1c655fd857d9fca454a2822da414e345c422db5b735441c5dabe8d628dbcc96` |
| 15 | GMR-003 | `src/greenmachine/config/versioning.py` | `c35f1dd5ede7cc285324058530219854f9aae40b878e9f99757ff7feaca5c07e` |
| 16 | GMR-003 | `src/greenmachine/domain/__init__.py` | `ec54ecb1b96d46e2c2be3af4811f171939061eb6ee37fe29dbcf7701c77b579f` |
| 17 | GMR-003 | `src/greenmachine/domain/_guards.py` | `dfe5e1c6c0b60e5002d1ac43d4f841360634c18d565b7d01d607518cbe7ad2af` |
| 18 | GMR-003 | `src/greenmachine/domain/entities.py` | `0b803f6bcafdeb7cbff75f2cd54e5697599d3afbcb6522ca90e06d2be7ae4b3c` |
| 19 | GMR-003 | `src/greenmachine/domain/enums.py` | `74df8ebfa411ac02461b1922fefed511eef17d67dabe4220db1a668b0667f3f6` |
| 20 | GMR-003 | `src/greenmachine/domain/envelope.py` | `102fe72430ae83a41e1df4ebefde81e10f61dd0f3ece0a04a7511a231777c7dc` |
| 21 | GMR-003 | `src/greenmachine/domain/errors.py` | `1fbeaabf9f4d478270287abb4c1574308f43dbb9331f6a606e7bae07117d6472` |
| 22 | GMR-003 | `src/greenmachine/domain/grade_result.py` | `fecdc6a510c0851917488db82f418a4bc9e6c4c3a287014ee99365680801bc25` |
| 23 | GMR-003 | `src/greenmachine/domain/observations.py` | `ad2b3b8c1554f2ab62d07b00bd444652499138aab282df40d9f923e69df59437` |
| 24 | GMR-003 | `src/greenmachine/domain/outcome.py` | `061b815c843a3f679737e18c93b92d8e548940292c31085b91ab872ef4e28707` |
| 25 | GMR-003 | `src/greenmachine/domain/results.py` | `8fdaa4c6abd7a7c469f81579a096c243a670e03aa23ea1b204c152b07a286a78` |
| 26 | GMR-003 | `src/greenmachine/domain/snapshot.py` | `bf1e523a2b0b0c52dc5f7d5584089147ba535522ad40afdbcc13d9d5d66496df` |
| 27 | GMR-003 | `src/greenmachine/domain/values.py` | `12b705e85c4a96e1b79b6880cacaddf8ed1d572a79ae9dbf165421fddae3d7d0` |
| 28 | GMR-003 | `src/greenmachine/scoring/__init__.py` | `b0120dfa17b84b0155d2644641909f157e2a5ca546b0311fa50875c4d26d18f5` |
| 29 | GMR-003 | `src/greenmachine/scoring/engine.py` | `c5ae5f79214055a6033cac10c809f0257d5f4503bc697c24772f66146dc38450` |
| 30 | GMR-003 | `src/greenmachine/scoring/errors.py` | `8bf833217a790d14db0cd10dbf8214f12988c6a3d0e7a8afb6f004a5e5acdc11` |
| 31 | GMR-003 | `src/greenmachine/evaluation/__init__.py` | `bdfcc540005dee138c1f5318994fec4b5ac7a8aed090bca04a7728d8bffeb039` |
| 32 | GMR-003 | `src/greenmachine/evaluation/errors.py` | `b90390d42cce7b1e9a8a32e1cf61991a3e1b5a8210a6781ab5cfea310058f5fc` |
| 33 | GMR-003 | `src/greenmachine/evaluation/serialization.py` | `5090dd197a5046cd4fe43f0797663c082bea852ee9e7b5c8ec6e00ebbc6e1b03` |
| 34 | GMR-002 | `.github/workflows/ci.yml` | `1418c523ffa620f806bb885aa74caecfada4836b6841636b8bfb825db7fb7fc2` |
| 35 | SUPERSEDED-000A | `.gitignore` | `b2a157c86c39fd51aeda4345e04d51c9241bd842474874bc0b1d0ef625ecbf41` |
| 36 | GMR-001 | `.pre-commit-config.yaml` | `1324be5fb52ec28e8a618af44e1ee24724294bb58fe18dd57f5bd33e0be391ab` |
| 37 | GMR-001 | `Makefile` | `7f02ca56f3912f0d7b7552b5577c4908fc09986578e56bde922d7d58f7737d0e` |
| 38 | GMR-001 | `pyproject.toml` | `9346f81343918467b6ee70bdac4617687e9c011fca3f1a3292bb2115c833ff3e` |
| 39 | GMR-001 | `requirements.txt` | `5bd426137913371b6ae198c2a4e53e5b720e42f668d7729e3e7dcb07c0df671f` |
| 40 | GMR-003 | `tests/README.md` | `dcc5807b6641c056a38d98b745e0561207d9292367c3ebcc4e3250193abd65f0` |
| 41 | GMR-003 | `tests/conftest.py` | `efc8b7cf70255f08e6e8b0f2d1047740ca317218423771815734f8fe2b5ef8c8` |
| 42 | GMR-003 | `tests/network_guard/child_bootstrap.py` | `a37bd007ba328cd34ce77b22d2d8e6398440cf0924a814ab48d26b68e927fb28` |
| 43 | GMR-003 | `tests/network_guard/greenmachine_network_guard.py` | `bef0f2c4eecc8b4a1692d3b5e7118340715650077a13bb4f494f3cdefae1b245` |
| 44 | GMR-003 | `tests/network_guard/guarded_child.py` | `c8f3ae80ed7a4beadb0af6aa445535f5810f5620e472450980988c9ce08a41e6` |
| 45 | GMR-003 | `tests/network_guard/sitecustomize.py` | `e406a90456a85b5b5d336481c7ff47d8dbb41bf7e94f4baa9c93b6a9c68b32da` |
| 46 | GMR-003 | `tests/architecture/static_analysis.py` | `c2fb37e08a310bde215f4b6afd6db066ec6922997c581fe27450478a7702a8c6` |
| 47 | GMR-003 | `tests/architecture/test_config_boundaries.py` | `3924679d1b6437ae30a19adad8fdf726c769c17959d1f01e35cb3799cf6e12c6` |
| 48 | GMR-003 | `tests/architecture/test_deployment_contract.py` | `15a49307fd5c03f944c04805891da5669bc0f96eda0f38310e27383b849d8c31` |
| 49 | GMR-003 | `tests/architecture/test_determinism_boundaries.py` | `4cec41be5a5e97185d4d444d02cc2b0c5835819aa82cbe2351f5fa9c02536a24` |
| 50 | GMR-003 | `tests/architecture/test_evaluation_boundaries.py` | `067cb6bc74248f47022c7a8a3d7157dd4dd5e815f60c6cfde622115d0f240c19` |
| 51 | GMR-003 | `tests/architecture/test_exception_handling.py` | `fa9a1dfd8aad2ec43d3da4d9e78b2ede50e67886ac1be0771ee86770b00852bf` |
| 52 | GMR-003 | `tests/architecture/test_golden_boundaries.py` | `6fd2066c2d6d7afcdabe2dd26363f148f81be89c5b0043398ba13856c316d4a9` |
| 53 | GMR-003 | `tests/architecture/test_import_boundaries.py` | `4d9fd145f62e7164898bfd8fef7fa95ceaaaa9d73cd1bb80694d3b7587dafb4b` |
| 54 | GMR-003 | `tests/architecture/test_scoring_boundaries.py` | `065149f4c490ac89859a5b28c1ba3a3ef36af05b5058354ba5f48b3aa16028c0` |
| 55 | GMR-003 | `scripts/update_goldens.py` | `ded19b9e98c54a5402cafde69cf820fe5077fba083803cd32f6131248c2f8b28` |
| 56 | GMR-003 | `tests/golden/__init__.py` | `f835628007cae263b3afa3ea155bf1abc95f350e616b94aa29e78c61c4a0c6c9` |
| 57 | GMR-003 | `tests/golden/cases/synthetic-long-term-evaluated/case.json` | `cdf1b94e77b5b1a6d3294af70a14ddfda4fcc48e3a74380dba3345ed4692eb91` |
| 58 | GMR-003 | `tests/golden/cases/synthetic-long-term-evaluated/expected_grade_result.json` | `2ce6558ad925b584a8bb14f1e5adb17e4b78e3698e393d9b6cff659422c44769` |
| 59 | GMR-003 | `tests/golden/cases/synthetic-long-term-evaluated/input_snapshot.json` | `7fe468ef14066fbab384ab3e73a719311d3aa8d0171e3bca2296eb1186ac1ab7` |
| 60 | GMR-003 | `tests/golden/cases/synthetic-recent-evaluated/case.json` | `8aa1d0fc8b5e3a2bb8fbb366e9fd61d9a9ff2d79140ad4e73fc69e5dc7b50632` |
| 61 | GMR-003 | `tests/golden/cases/synthetic-recent-evaluated/expected_grade_result.json` | `9dfaee296090e80ac7ecaa3c0d08a35e507f4dd08f1f62bbeac74515385629ff` |
| 62 | GMR-003 | `tests/golden/cases/synthetic-recent-evaluated/input_snapshot.json` | `a1bf90b4851c8cc9b7e3f60bd6356eae571c80e3d271dc1e4038a247e6112895` |
| 63 | GMR-003 | `tests/golden/cases/synthetic-recent-not-evaluable/case.json` | `e9517468a6aa62057424d3fa7a6de5fd4972d97bf6222b3507dc89ee75debff9` |
| 64 | GMR-003 | `tests/golden/cases/synthetic-recent-not-evaluable/expected_grade_result.json` | `9312028d503fa70e0094fd8529bcaa54f04e03e4ccb44d7b40b6c136567a1de6` |
| 65 | GMR-003 | `tests/golden/cases/synthetic-recent-not-evaluable/input_snapshot.json` | `0dec382d346dab1c469367913e95c45af564cdd9a3782fcac6ea351298f2d211` |
| 66 | GMR-003 | `tests/golden/runner.py` | `5d2e01b1d8df4bf346155f52a9d06c10bbd51244074edc69d6ed09ed8d41d6e9` |
| 67 | GMR-003 | `tests/golden/stub_scorer.py` | `8cfd4406dfc47ef77564cbc8be3fb5392eb513657240c786d761f9f97cd8b6c7` |
| 68 | GMR-003 | `tests/golden/test_golden_cases.py` | `5cc7130b6149b9d88ff6311423de7b23aeaf2355ec6893ac74eb0df5ffe61883` |
| 69 | GMR-003 | `tests/unit/golden/test_case_confinement.py` | `10f68a2d1c3440753881c8216254777e573c5d8aef4c93e9871f83157af14fbf` |
| 70 | GMR-003 | `tests/unit/golden/test_case_format.py` | `02a2eb4ac06830229f00484aa49dea58fa30108780dc0ea72fc17898746c6279` |
| 71 | GMR-003 | `tests/unit/golden/test_golden_diffs.py` | `a96d92e4d1364a4e791736e9dc9846b8a4bda6cfa02ef002647d34e78c088a93` |
| 72 | GMR-003 | `tests/unit/golden/test_hashseed_determinism.py` | `997ddbb5b97b745367e0cfe47063eb4fc76b88529646f77daf79de94c3c12178` |
| 73 | GMR-003 | `tests/unit/golden/test_network_blocking.py` | `6e7926043d752ad9571a9fd73403590c406354dea97b5cb74407fe80d26b9107` |
| 74 | GMR-003 | `tests/unit/golden/test_profile_separation.py` | `51fd30455f96961a21ba27bbd33767aaacf083a776b9f98c1f7e9e7954a119a7` |
| 75 | GMR-003 | `tests/unit/golden/test_runner_execution.py` | `d7a6c3d14288981086cf992923c6ba72d46e7a22f99cc907a1bc3413d9c5b390` |
| 76 | GMR-003 | `tests/unit/golden/test_stub_scorer.py` | `e367382add0d865b099d44450c0aefb79fd24d4bea0eb46055b177dc7f5a0c6f` |
| 77 | GMR-003 | `tests/unit/golden/test_update_script.py` | `f60b0839c33486aa9b0f516dcd36d8a8927b68221d9a7bf411a786af4848edfa` |
| 78 | GMR-003 | `tests/fixtures/config/invalid/README.md` | `959a6d2f3870a0b343dd116bf5d58ceb60b5671d6b3c600dce43adffec072987` |
| 79 | GMR-003 | `tests/fixtures/config/invalid/duplicate_key.yaml` | `e321ffc9b25a5073f66f91796c46cac6bb8f161e8a46f71f6f7c347a2357449f` |
| 80 | GMR-003 | `tests/fixtures/config/invalid/empty.yaml` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 81 | GMR-003 | `tests/fixtures/config/invalid/malformed.yaml` | `8d345c28381c2f85e5a2213ac5893b2967d6872fa730bd46fa4a6485ca568834` |
| 82 | GMR-003 | `tests/fixtures/config/invalid/merge_key.yaml` | `e74ec6dc27de48a11fb7dfbefbc0734c79bb2c80ecb7fa52b1b754c0263c90d1` |
| 83 | GMR-003 | `tests/fixtures/config/invalid/non_mapping_root.yaml` | `87181bd294c60784217bc932a025342e678567e8951dda0a34ee07aef4bf698f` |
| 84 | GMR-003 | `tests/fixtures/config/invalid/two_documents.yaml` | `7125f8d4505bb80f7ddf459d27d6890739d9f9f6ced19d3caf58545373edd591` |
| 85 | GMR-003 | `tests/fixtures/config/invalid/yaml_alias.yaml` | `0b6fb49f2838ebaedafc02e018468b320b8ca6bb9e072e7acdae054b752ebeeb` |
| 86 | GMR-003 | `tests/fixtures/config/valid/complete_synthetic.yaml` | `46f22c37aa8fb7a181a77bb7d60851b63080d4528a15386134e65ff68bf826c4` |
| 87 | GMR-003 | `tests/fixtures/evaluations/evaluated_grade_result.json` | `51c003cc05242db5e80782832025cf8a44e219cf7a74d6b0cc1da4ce3e9dd02b` |
| 88 | GMR-003 | `tests/fixtures/evaluations/evaluation_envelope.json` | `e26d912c765bc4d84b7ab5734c7467a2ac8bd001f356f3b430f608b4a69b8c81` |
| 89 | GMR-003 | `tests/fixtures/evaluations/gm041_engine_snapshots.py` | `f34df2a3ceb9562853ecbab66251a05866b692c0dcd2b5f423309afbba5ba770` |
| 90 | GMR-003 | `tests/fixtures/evaluations/input_snapshot.json` | `a1bf90b4851c8cc9b7e3f60bd6356eae571c80e3d271dc1e4038a247e6112895` |
| 91 | GMR-003 | `tests/fixtures/evaluations/not_evaluable_grade_result.json` | `328b669573d1249fb22b6c1af828e5dbd1b8575548e1eae7c870bafc5d5fcf7b` |
| 92 | GMR-003 | `tests/fixtures/evaluations/outcome_record.json` | `88d0c7db0799f2915e8c9a35fabf861f8e4140add6c1db0fcde3a3fb303b7f64` |
| 93 | GMR-003 | `tests/fixtures/evaluations/synthetic_golden_cases.py` | `fbe57599be0c94f307c9ad9b555cad0dc08fc0a7dff19becf6c1e19d065d4935` |
| 94 | GMR-003 | `tests/fixtures/evaluations/synthetic_records.py` | `028379fb32471e68306a2e5bb0b92c79827f95018a52f43af6cf55314b909cfb` |
| 95 | GMR-003 | `tests/property/conftest.py` | `618cb392371d10daabb2c9a5b447ee6e8ec87ea1d3b344b3074287ee724e4cba` |
| 96 | GMR-003 | `tests/property/test_config_hashing.py` | `6f32ef2c7f857a900fe79c768b8353963169a5e819ad0000ef50fdf7af296ec4` |
| 97 | GMR-003 | `tests/property/test_determinism.py` | `1ec15f5199cc6a5bf42519e8472b6deffeb127a55c3bbca6ecd48edcd2b5219d` |
| 98 | GMR-003 | `tests/property/test_golden_properties.py` | `4bfb983b6e75b6511407036cbe4c1905c9dc9b4fb965a975173bdd9760c2ef0e` |
| 99 | GMR-003 | `tests/property/test_hypothesis_policy_documentation.py` | `030e2ff0539719d9d589eec577e90cd825efaee799cc643f4903e898327b83b9` |
| 100 | GMR-003 | `tests/property/test_hypothesis_profile_policy.py` | `b38c178f7832f5f64e102f6717582983bd8ebfb385ca7ef55d5e0393a4b316e2` |
| 101 | GMR-003 | `tests/property/test_record_determinism.py` | `44ef3dade45e93d6bcc618155074eeba25862f3dc8b03161dc8f108f67348531` |
| 102 | GMR-003 | `tests/unit/common/test_canonical_decimal.py` | `8dc5a993d1e9e0d3e4b499f3c4d6c7051e4e95eaedbbcb1c0a4dce3561b601e4` |
| 103 | GMR-003 | `tests/unit/common/test_clock.py` | `8404dfba3b31adb56c6b72a608ec4afddf9351f01b069016893b04f464001061` |
| 104 | GMR-003 | `tests/unit/common/test_errors.py` | `8f8f5e2ddda7a228eb8abeebef9ca251c21e72ec96d80d39888f4da6cc328406` |
| 105 | GMR-003 | `tests/unit/common/test_ids.py` | `72903bfbb7128f63302a4bb406830446a8925e5e717408c8b456076e209e5573` |
| 106 | GMR-003 | `tests/unit/common/test_intervals.py` | `192c62251a98f86588107ac8d6d23d7e50c0465b5f0e57bc1dd4de8c73e692a8` |
| 107 | GMR-003 | `tests/unit/common/test_logging.py` | `53957ad7794adb154a59ab9c6766a9898e167e194cb0771ee571e7067b82680b` |
| 108 | GMR-003 | `tests/unit/common/test_numeric_construction.py` | `3253d6b2bde364b3c45ecbe45fd558fb273bae282ba4d05d423df2c84b1a05f6` |
| 109 | GMR-003 | `tests/unit/common/test_numeric_context.py` | `3b5722d266b188284e3de4e54eafac88ee740b48e7d4096a25f16d4fa992960e` |
| 110 | GMR-003 | `tests/unit/common/test_serialization.py` | `0dcd8f92a5e73890651515d7bb2ffa3d662135841aa156ee56e1ab218b5a1752` |
| 111 | GMR-003 | `tests/unit/config/config_fixtures.py` | `4e6a4ecb10d18c89b39afde1425679bc19391def4532271d2ca4b49b0f6eb36e` |
| 112 | GMR-003 | `tests/unit/config/test_correction_r1.py` | `0456e56e92a145efecf336e811536c7e2715af8d07339d057cd9bde3b055b5c0` |
| 113 | GMR-003 | `tests/unit/config/test_correction_r2.py` | `c738a271abf4687843b9fc15525615f0b429259be7447e1222c18a9aaba623da` |
| 114 | GMR-003 | `tests/unit/config/test_correction_r3.py` | `13c00c9cfffb9dffaa76c8de8641ba0c9015ee643bec65ef55ce40888a0c5284` |
| 115 | GMR-003 | `tests/unit/config/test_edge_cases.py` | `301bf89fb0ae35e8df0291f8c98e8a89e79c2af977dfbfc8210ee3fa71b06304` |
| 116 | GMR-003 | `tests/unit/config/test_hashing.py` | `db04dc540f422cfdcadc11b54dbacd9caf0fbff41f954fbdcdd922f8cd9bbf54` |
| 117 | GMR-003 | `tests/unit/config/test_invariants.py` | `e8d1da8af663df168fb7b8574eb8df8ad477652a251e40b415e24744d5394882` |
| 118 | GMR-003 | `tests/unit/config/test_loader.py` | `fbd39c1f51421faa87e36d515949351b6276e1022328a6d7f1c86ba81c118cd3` |
| 119 | GMR-003 | `tests/unit/config/test_nonproduction_config_location.py` | `dfb981ca62999fcf73c86d13372e24d0dbf7e5e6e788a3f7291c2fd1fd826869` |
| 120 | GMR-003 | `tests/unit/config/test_schema.py` | `a1ca1fd04caa4b1f6ab646bbe1158cdbae266d0ab496be0b387783191510c2c4` |
| 121 | GMR-003 | `tests/unit/config/test_versioning.py` | `bfd0993c157e0a5c327d62b96c01b0bae0c58a527a13a51a9b4b41818b47410c` |
| 122 | GMR-003 | `tests/unit/domain/domain_builders.py` | `7d405fde3aeb0e93c022a14240fa1d323a48d1e479500766e7ffd66598dbfe91` |
| 123 | GMR-003 | `tests/unit/domain/test_coherence.py` | `bd1c3f8eea548b299ba9a879a04a317bf667aa2712be0a3b1aca820eb916c12a` |
| 124 | GMR-003 | `tests/unit/domain/test_entities.py` | `d961ac08378008caa5885518bf916ef5b9aad273fea8501eddc3aeb93ab1742c` |
| 125 | GMR-003 | `tests/unit/domain/test_enums.py` | `85fb81f8b4001aa5c9376fc2cb7adee7ec0bd65cff44064c480d8ca3c6e4d6c3` |
| 126 | GMR-003 | `tests/unit/domain/test_evaluation_envelope.py` | `885024abc45a63eff112d3c0ee5604e802bc3e61dd81ad77e48ad74dc58fc84d` |
| 127 | GMR-003 | `tests/unit/domain/test_glossary_drift.py` | `381e88a8bfab3d219228bf55cd92e3c0d616a039a6970a66dda201073de4b9ad` |
| 128 | GMR-003 | `tests/unit/domain/test_grade_result.py` | `d447997fb2defced10096b8073239b7a3d21962f600b51fcb9589b277650bb8b` |
| 129 | GMR-003 | `tests/unit/domain/test_guards.py` | `5bda1180c10cffd2fb78c19a58dfe3e567b0c6b02e07ad013f82e1ec09daa0fa` |
| 130 | GMR-003 | `tests/unit/domain/test_immutability.py` | `6417fd2463f37ba2ba14d730bea2d7645f6665328d0738b8330cdc9c50039640` |
| 131 | GMR-003 | `tests/unit/domain/test_input_snapshot.py` | `cbcd8f8ba6233ec3d95cbf5461b74e78e165d5146140c1b5b4e672db6ae084d4` |
| 132 | GMR-003 | `tests/unit/domain/test_observations.py` | `306631d00f6b0455e92dcb039ead4f30bfce408577dfcea09a8e5d185022fd3e` |
| 133 | GMR-003 | `tests/unit/domain/test_outcome_record.py` | `3c12225d711771fc50f49f5457249f36a8fc68c4d305f0393e3c45583c848655` |
| 134 | GMR-003 | `tests/unit/domain/test_results.py` | `a6a0962bedded68626a20e628b65148d5e29307f911e46c17688602bd267e4fa` |
| 135 | GMR-003 | `tests/unit/domain/test_sha256_digest.py` | `023b2ed4ffeeee15eb4c9b30611e547d806abcdfe17c133de144f18dcb353593` |
| 136 | GMR-003 | `tests/unit/domain/test_values.py` | `ea66a5634f7ba0ff8c8fdf20ba2b021b438414504afd6f3c37ba318b179c4aab` |
| 137 | GMR-003 | `tests/unit/evaluation/test_record_serialization.py` | `ac0cece0df27fe610bdc255027d374d5692a38e72997fa6aa5fde4f4629e00eb` |
| 138 | GMR-003 | `tests/unit/evaluation/test_snapshot_identity.py` | `58707384f3ca4511f3f2c6c4ad272049fb1c5098b452efbc6872704c5b1bf8ce` |
| 139 | GMR-003 | `tests/unit/scoring/test_engine.py` | `397cde5b8fc80e7aa1975749993137696ba88cea943431f8a962d560af014f38` |
| 140 | GMR-003 | `tests/unit/test_package.py` | `b19ac35174824435ddcd7ba37bd3874237c29eb9a84f89643a4064be09362dee` |
| 141 | GMR-003 | `config/nonproduction/gm041_engine_synthetic.yaml` | `51dac8cccfbba66d69a9dd6b744f4f077ecb1a37bdbaf7185242f0c224a5ece5` |
| 142 | GMR-003 | `docs/GLOSSARY.md` | `6be7a266f61b55de9fbca79c94797474ccf7d3c09d5576891f521982e9f327e7` |
| 143 | GMR-003 | `docs/adr/0008-golden-testing-strategy.md` | `4836ac5a868276ea75152f4f01aaefa73c8f16384497a6f0eaf77cb7b7c8e880` |
| 144 | GMR-003 | `docs/STREAMLIT_PROTOTYPE.md` | `7abfe8ac4d6c8a464e664c05d9c8ee0409c119b882a91b3212482d79aefbc60a` |
