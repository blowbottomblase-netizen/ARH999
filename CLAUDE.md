# OKX AI TRADE

OKX 交易自动化工作台 — Python SDK + CLI + MCP 集成。

## 目录结构

```
F:\OKX AI TRADE\
├── .okx\                   # OKX CLI 全局配置副本（主配置在 ~/.okx/）
│   └── config.toml         # API 凭证（agent MCP profile）
├── okx\                    # Python OKX SDK 包
├── examples\               # SDK 使用示例
├── build\                  # 构建输出
├── CLAUDE.md               # 本文件 — Claude Code 会话上下文
├── setup.py                # Python 包安装
├── requirements.txt        # Python 依赖
└── readme.md               # 原始说明文档
```

## 环境配置

### CLI 工具
- `okx` — OKX Trade CLI v1.3.8（命令 `okx`，非 `okx-trade-cli`）
- `okx-trade-mcp` — OKX MCP Server v1.3.8
- Profile: **agent MCP**（已设为默认，实盘环境）
- 配置文件路径: `~/.okx/config.toml`（CLI 读取的路径，`F:\OKX AI TRADE\.okx\` 是副本）

### API 权限
- 当前 Key: `514ddc5e-****-****-****-****d11e`（尾号 d11e）
- 权限: 读取 + 交易
- 环境: live（实盘）

### 账户摘要
| 币种 | 可用 | 状态 |
|------|------|------|
| BTC | 0.01583613 | 活期 |
| USDT | ~20.24 | 活期 |
| ETH | ~0.00000136 | 活期 |

## 常用命令

```bash
# 行情查询
okx market ticker BTC-USDT                    # BTC 实时行情
okx market funding-rate BTC-USDT-SWAP         # 永续合约资金费率
okx market candles BTC-USDT --bar 1H          # K 线数据

# 账户
okx account balance                            # 查看余额和持仓
okx account positions                          # 查看持仓

# 现货交易
okx spot place --instId BTC-USDT --side buy --ordType limit --sz 0.001 --px 63000
okx spot place --instId BTC-USDT --side buy --ordType market --sz 100 --tgtCcy quote_ccy
okx spot orders --instId BTC-USDT             # 查看订单

# 模拟盘（--demo）
okx --demo spot place --instId BTC-USDT --side buy --ordType market --sz 100 --tgtCcy quote_ccy

# 合约交易
okx swap place --instId BTC-USDT-SWAP --side long --ordType market --sz 1

# 配置
okx config show                                # 查看当前配置
okx config init                                # 交互式重新配置 API
```

## 历史记录

### 2026-06-13 — 初始配置
- 安装 `@okx_ai/okx-trade-mcp@1.3.8` 和 `@okx_ai/okx-trade-cli@1.3.8`
- 创建 `agent MCP` profile，配置 API Key (尾号 d11e)
- 首次查询 BTC 价格 ($64,001)，账户余额验证通过
- 尝试 `npx skills add okx/agent-skills` 失败（GitHub 被阻断）
- 替代方案: `okx skill` 模块管理 Agent Skills
