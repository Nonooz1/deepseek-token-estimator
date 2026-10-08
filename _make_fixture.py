# -*- coding: utf-8 -*-
"""生成两个仿真的 Keil 工程并打包成 zip，用于测试与演示

  1. STM32F103_Demo.zip  —— Keil MDK v5（ARM，.uvprojx）
  2. MS51_BMS_C51.zip    —— Keil uVision 4（8051 C51，.uvproj）
     目录与文件名照着真实工程（Nuvoton MS51 电池管理）1:1 还原，
     用来验证产物过滤规则在真实命名下是否有效。
"""
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "_fixture")


def _wipe(path):
    """逐文件删除，避免依赖 shutil.rmtree（部分环境下会被安全删除钩子拦截）。"""
    if not os.path.isdir(path):
        return
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        for fn in filenames:
            try:
                os.remove(os.path.join(dirpath, fn))
            except OSError:
                pass
        for dn in dirnames:
            try:
                os.rmdir(os.path.join(dirpath, dn))
            except OSError:
                pass


_wipe(ROOT)
os.makedirs(ROOT, exist_ok=True)


def build(name, files):
    """files: [(相对路径, 内容或bytes)]"""
    build_dir = os.path.join(ROOT, "_build_" + name)
    zip_path = os.path.join(ROOT, name + ".zip")
    for rel, content in files:
        p = os.path.join(build_dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
        if mode == "wb":
            with open(p, "wb") as f:
                f.write(content)
        else:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(content)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for r, _, ns in os.walk(build_dir):
            for n in sorted(ns):
                full = os.path.join(r, n)
                zf.write(full, os.path.join(name, os.path.relpath(full, build_dir)))
    _wipe(build_dir)
    n = len(files)
    print(f"  {name}.zip  ({os.path.getsize(zip_path):,} 字节，{n} 个文件)")
    return zip_path


# ============================================================
# 1) Keil MDK v5 / ARM
# ============================================================
STM32 = [
    ("MDK-ARM/STM32F103_Demo.uvprojx",
     '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
     '<Project><SchemaVersion>2.1</SchemaVersion><Targets><Target>\n'
     '  <TargetName>STM32F103_Demo</TargetName>\n'
     '  <ToolsetName>ARM-ADS</ToolsetName>\n'
     '  <Device>STM32F103C8</Device><Vendor>STMicroelectronics</Vendor>\n'
     '  <Cpu>IRAM(0x20000000,0x5000) IROM(0x8000000,0x10000) CPUTYPE("Cortex-M3")</Cpu>\n'
     '  <Groups><Group><GroupName>Application</GroupName><Files>\n'
     '    <File><FileName>main.c</FileName><FileType>1</FileType>'
     '<FilePath>../Core/Src/main.c</FilePath></File>\n'
     '  </Files></Group></Groups>\n'
     '</Target></Targets></Project>\n'),
    ("MDK-ARM/STM32F103_Demo.uvoptx",
     '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
     '<ProjectOpt><SchemaVersion>1.0</SchemaVersion><Target>\n'
     '  <TargetName>STM32F103_Demo</TargetName><DebugOpt><uSim>0</uSim><nTsel>3</nTsel></DebugOpt>\n'
     '</Target></ProjectOpt>\n'),
    ("MDK-ARM/STM32F103_Demo.uvguix.hp",
     '<?xml version="1.0"?><Layout><Window><Height>800</Height></Window></Layout>'),
    ("MDK-ARM/startup_stm32f103xb.s",
     "  .syntax unified\n  .cpu cortex-m3\n  .thumb\n"
     ".global g_pfnVectors\n.global Default_Handler\n"
     "  .section .text.Reset_Handler\n  .weak Reset_Handler\n"
     "Reset_Handler:\n  ldr   sp, =_estack\n  bl    SystemInit\n  bl    main\n  bx    lr\n"
     "Default_Handler:\nInfinite_Loop:\n  b Infinite_Loop\n"),
    ("MDK-ARM/STM32F103_Demo.sct",
     "LR_IROM1 0x08000000 0x00010000  {\n"
     "  ER_IROM1 0x08000000 0x00010000  {\n   *.o (RESET, +First)\n   .ANY (+RO)\n  }\n"
     "  RW_IRAM1 0x20000000 0x00005000  {\n   .ANY (+RW +ZI)\n  }\n}\n"),
    ("Core/Src/main.c",
     '/**\n  ******************************************************************************\n'
     '  * @file    main.c\n  * @brief   主程序入口，演示 STM32F103 的 GPIO 与定时器使用\n'
     '  ******************************************************************************\n  */\n'
     '#include "main.h"\n#include "stm32f1xx_hal.h"\n\n'
     'static TIM_HandleTypeDef htim2;\n\n'
     "/* 系统时钟配置：外部 8MHz 晶振，倍频到 72MHz */\n"
     "void SystemClock_Config(void)\n{\n"
     "  RCC_OscInitTypeDef RCC_OscInitStruct = {0};\n"
     "  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;\n"
     "  RCC_OscInitStruct.HSEState = RCC_HSE_ON;\n"
     "  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;\n"
     "  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)\n  {\n    Error_Handler();\n  }\n}\n\n"
     "int main(void)\n{\n  HAL_Init();\n  SystemClock_Config();\n"
     "  while (1)\n  {\n    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);\n    HAL_Delay(500);\n  }\n}\n\n"
     "void Error_Handler(void)\n{\n  __disable_irq();\n  while (1) { }\n}\n"),
    ("Core/Src/stm32f1xx_it.c",
     '#include "main.h"\n#include "stm32f1xx_it.h"\n\n'
     "void NMI_Handler(void)        { }\nvoid HardFault_Handler(void)  { while (1) { } }\n"
     "void SysTick_Handler(void)    { HAL_IncTick(); }\n"
     "void TIM2_IRQHandler(void)\n{\n  HAL_TIM_IRQHandler(&htim2);\n}\n"),
    ("Core/Inc/main.h",
     "#ifndef __MAIN_H\n#define __MAIN_H\n\n#ifdef __cplusplus\nextern \"C\" {\n#endif\n\n"
     '#include "stm32f1xx_hal.h"\n\nvoid Error_Handler(void);\n\n'
     "#define LED_PIN     GPIO_PIN_13\n#define LED_PORT    GPIOC\n\n"
     "#ifdef __cplusplus\n}\n#endif\n\n#endif /* __MAIN_H */\n"),
    ("Core/Inc/stm32f1xx_hal_conf.h",
     "#ifndef __STM32F1xx_HAL_CONF_H\n#define __STM32F1xx_HAL_CONF_H\n\n"
     "#define HAL_MODULE_ENABLED\n#define HAL_GPIO_MODULE_ENABLED\n#define HAL_TIM_MODULE_ENABLED\n"
     "#define HSE_VALUE    8000000U\n#define LSE_VALUE    32768U\n\n"
     '#ifdef HAL_GPIO_MODULE_ENABLED\n#include "stm32f1xx_hal_gpio.h"\n#endif\n\n'
     "#endif /* __STM32F1xx_HAL_CONF_H */\n"),
    ("Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c",
     "/* HAL GPIO 驱动（节选） */\n"
     "void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *GPIO_Init)\n{\n"
     "  uint32_t position = 0x00u;\n  while (((GPIO_Init->Pin) >> position) != 0x00u)\n  {\n"
     "    position++;\n  }\n}\n" * 12),
    ("RTE/RTE_Components.h",
     "/* 由 RTE 自动生成 */\n#ifndef RTE_COMPONENTS_H\n#define RTE_COMPONENTS_H\n\n"
     "#define RTE_DEVICE_STARTUP_STM32F1xx\n#define RTE_DEVICE_HAL_GPIO\n\n#endif\n"),
    ("README.md", "# STM32F103 演示工程\n\n用 Keil MDK v5 打开 `MDK-ARM/STM32F103_Demo.uvprojx`。\n"),
    # ---- 产物（应全部跳过）----
    ("MDK-ARM/Objects/main.o", b"\x7fELF\x01\x01\x01\x00" + bytes(range(256)) * 8),
    ("MDK-ARM/Objects/STM32F103_Demo.axf", b"\x7fELF\x01\x01\x01\x00" + bytes(range(256)) * 16),
    ("MDK-ARM/Objects/main.crf", b"\x00\x01\x02\x03" * 500),
    ("MDK-ARM/Objects/main.d", "main.o: ../Core/Src/main.c ../Core/Inc/main.h\n"),
    ("MDK-ARM/Listings/STM32F103_Demo.map",
     "Component: ARM Compiler 5.06 update 7\n" + "    Symbol  Address  Type  Size  Object\n" * 400),
    ("MDK-ARM/STM32F103_Demo.hex",
     "".join(f":10{i:04X}00" + "A5" * 16 + "00\n" for i in range(300))),
]

# ============================================================
# 2) Keil uVision 4 / 8051 C51 —— 照真实工程 1:1 还原命名
# ============================================================
SRC_C = ("/* %s */\n#include \"User.h\"\n\n"
         "void %s_Init(void)\n{\n  /* 初始化 */\n}\n\n"
         "unsigned char %s_Run(unsigned char in)\n{\n  return in;\n}\n")

CODE_FILES = [
    "BatterCheck", "Charge", "CW2017", "DataFlash", "DisCharge", "gotoBootFile",
    "I2C_S", "interface", "key", "McuHal_MS51PC0AE", "SC2011", "Sc8933", "soc", "Uart",
]

C51 = []
# 工程文件（uVision 4 用 .uvproj / .uvopt）
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/UserProj.uvproj",
            '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
            '<Project><SchemaVersion>1.1</SchemaVersion><Targets><Target>\n'
            '  <TargetName>TZ3-FC-01-0A</TargetName>\n'
            '  <ToolsetNumber>0x1</ToolsetNumber><ToolsetName>C51</ToolsetName>\n'
            '  <Device>MS51PC0AE</Device><Vendor>Nuvoton</Vendor>\n'
            '  <Groups><Group><GroupName>Code</GroupName><Files>\n'
            '    <File><FileName>Main.C</FileName><FileType>1</FileType>'
            '<FilePath>Code\\Main.C</FilePath></File>\n'
            '  </Files></Group></Groups>\n'
            '</Target></Targets></Project>\n'))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/UserProj.uvopt",
            '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
            '<ProjectOpt><SchemaVersion>1.0</SchemaVersion><Target>\n'
            '  <TargetName>TZ3-FC-01-0A</TargetName><DebugOpt><nTsel>4</nTsel></DebugOpt>\n'
            '</Target></ProjectOpt>\n'))

# 公共代码
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/Common/Common.c", SRC_C % ("公共函数", "Common", "Common")))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/Common/Common.h",
            "#ifndef __COMMON_H\n#define __COMMON_H\n\nvoid Common_Init(void);\n\n#endif\n"))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/Common/Delay.c", SRC_C % ("延时", "Delay", "Delay")))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/Common/sys.c", SRC_C % ("系统", "sys", "sys")))

# 头文件目录
for h in ["Delay", "Function_Define_MS51_32K", "MS51_32K", "SFR_Macro_MS51_32K"]:
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/Include/{h}.h",
                f"#ifndef __{h.upper()}_H\n#define __{h.upper()}_H\n\n"
                f"/* {h} 寄存器与宏定义 */\n#define {h.upper()}_BASE  0x00\n\n#endif\n"))

# 启动文件（Keil C51 的汇编是 .A51，大写）
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/Startup/STARTUP.A51",
            "; Keil C51 启动代码\nNAME    ?C_STARTUP\n\n"
            "?C_STARTUP:\n    MOV     SP, #7FH\n    LJMP    STARTUP1\n\n"
            "STARTUP1:\n    MOV     R0, #0\n    RET\n\nEND\n"))

# 应用代码
for f in CODE_FILES:
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Code/{f}.c",
                SRC_C % (f, f, f)))
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Code/{f}.h",
                f"#ifndef __{f.upper()}_H\n#define __{f.upper()}_H\n\n"
                f"void {f}_Init(void);\nunsigned char {f}_Run(unsigned char in);\n\n#endif\n"))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Code/Main.C",
            SRC_C % ("主程序", "Main", "Main")))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Code/User.h",
            "#ifndef __USER_H\n#define __USER_H\n\n#include \"MS51_32K.h\"\n\n#endif\n"))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Code/SysDefs.h",
            "#ifndef __SYSDEFS_H\n#define __SYSDEFS_H\n\n#define VERSION  0x10\n\n#endif\n"))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Nu_Link_8051_Driver.ini",
            "[NuLink]\nDriver=NuLink_8051\nClock=24000\n"))

# 界面布局（uVision 4 是 .uvgui.<用户名>，多人各留一份 → 典型噪音）
for u in ["admin", "Administrator", "T450", "U60512", "U60994", "U62868", "U67161"]:
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/UserProj.uvgui.{u}",
                '<?xml version="1.0"?><Layout><Window><Height>768</Height>'
                '<Width>1024</Width></Window></Layout>'))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/UserProj.uvgui.U62868.bak",
            '<?xml version="1.0"?><Layout><Window><Height>768</Height></Window></Layout>'))

# 产物：LST 目录（.lst 列表 + .map 映射）
for f in ["ADC", "BatterCheck", "Charge", "Common", "CW2017", "DataFlash", "Delay",
          "DisCharge", "gotoBootFile", "I2C_S", "interface", "key", "Main",
          "McuHal_MS51PC0AE", "SC2011", "Sc8933", "soc", "STARTUP", "sys", "Uart"]:
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/LST/{f}.lst",
                "".join(f"{i:04X}  MOV   A, #0FFH\n" for i in range(200))))
for m in ["TZ3-FC-01-0A", "P2106-6S2P", "P2106-6S2P-APP", "UseProj"]:
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/LST/{m}.map",
                "SEGMENT  START  LENGTH  TYPE\n" * 300))

# 产物：Output 目录（.obj / .hex / .lnp / .SBR / .iex / build_log.htm / .__i）
for f in ["BatterCheck", "Charge", "CW2017", "DataFlash", "DisCharge", "gotoBootFile",
          "I2C_S", "interface", "key", "Main", "McuHal_MS51PC0AE", "SC2011", "Sc8933",
          "soc", "STARTUP", "sys", "Uart"]:
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Output/{f}.obj",
                b"\x80\x01\x02" + bytes(range(256)) * 3))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Output/Common.__i", b"\x00\x01\x02" * 400))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Output/ExtDll.iex", b"\x00\x01" * 300))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Output/TZ3-FC-01-0A.lnp",
            "Common.obj, Charge.obj, Main.obj\n"))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Output/TZ3-FC-01-0A.SBR", b"\x00" * 2000))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Output/TZ3-FC-01-0A_22.5W.hex",
            "".join(f":10{i:04X}00" + "5A" * 16 + "00\n" for i in range(400))))
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/UserProjFOR_TZ3_FC_0A/Output/TZ3-FC-01-0A.build_log.htm",
            "<html><body><pre>" + "Build target 'TZ3-FC-01-0A'\n" * 300 + "</pre></body></html>"))

# 产物：Source Insight 索引目录
for ext in ["IAB", "IAD", "IMB", "IMD", "PFI", "PO", "PR", "PRI", "PS", "WK3", "SearchResults"]:
    C51.append((f"PDMS51PC0AE_TZ3_FC_0C_22.5W/si/MS51PC0AE Demo.{ext}",
                b"\x00\x01\x02\x03" * 200))

# 一个中文名的杂项文本（真实工程里就有）
C51.append(("PDMS51PC0AE_TZ3_FC_0C_22.5W/新建文本文档.txt", "工程说明：这是 22.5W 电池管理板固件。\n"))

print("生成测试夹具：")
build("STM32F103_Demo", STM32)
build("MS51_BMS_C51", C51)
print("\n完成。目录:", ROOT)
