# 实现计划 (Nginx + FastAPI + Python)

## 技术栈概览

| 组件 | 技术选型 |
|------|---------|
| Web框架 | FastAPI + Uvicorn |
| 网关层 | Nginx (反向代理/负载均衡/限流) |
| ORM | SQLAlchemy 2.0 (异步) |
| 数据校验 | Pydantic v2 |
| 消息队列 | Kafka (aiokafka) |
| 缓存 | Redis (aioredis) |
| 认证 | JWT (python-jose) |
| 配置中心 | Consul / 环境变量 |
| 属性测试 | Hypothesis |
| 单元测试 | pytest + pytest-asyncio |

---

## 第一阶段：基础设施搭建

- [ ] 1. 搭建项目骨架
  - [ ] 1.1 创建 Python 多模块项目结构
    - 创建项目根目录和 pyproject.toml
    - 创建 erp_common 公共模块
    - 创建 erp_gateway (Nginx 配置)
    - 创建 10 个微服务模块 (item/user/purchase/production/job/stock/cost/order/member/promo)
    - 目录结构：
      ```
      erp/
      ├── pyproject.toml
      ├── docker-compose.yml
      ├── nginx/
      │   └── nginx.conf
      ├── erp_common/
      │   ├── __init__.py
      │   ├── models/
      │   ├── schemas/
      │   ├── utils/
      │   └── events/
      ├── services/
      │   ├── item_service/
      │   ├── user_service/
      │   ├── stock_service/
      │   └── ... (其他服务)
      └── tests/
      ```
    - _需求: 架构设计_
  - [ ] 1.2 配置公共依赖
    - 配置 FastAPI、SQLAlchemy、Pydantic 依赖
    - 配置 aiokafka、aioredis 依赖
    - 配置 hypothesis 属性测试框架
    - 配置 pytest、pytest-asyncio 测试依赖
    - _需求: 测试策略_
  - [ ] 1.3 创建公共组件
    - 创建统一响应结果类 `Result[T]`
    - 创建统一异常处理中间件
    - 创建分页查询基类 `PageQuery`、`PageResult`
    - 创建领域事件基类 `DomainEvent`
    - 创建数据库会话管理 `get_db()`
    - _需求: 12.4_

- [ ] 2. 数据库初始化
  - [ ] 2.1 创建数据库初始化脚本
    - 编写所有表的 SQLAlchemy 模型
    - 编写 Alembic 迁移脚本
    - 编写初始化数据脚本（角色、权限等）
    - _需求: 数据模型设计_

- [ ] 3. Nginx 网关配置
  - [ ] 3.1 配置 Nginx 反向代理
    - 配置各服务的 upstream
    - 配置路由规则 /item/* /user/* /stock/* 等
    - _需求: 14.5_
  - [ ] 3.2 配置限流和安全
    - 配置 limit_req_zone 限流
    - 配置 CORS 跨域
    - 配置 SSL/TLS (可选)
    - _需求: 14.3_

---

## 第二阶段：核心服务实现

- [ ] 4. 商品中心 (item_service)
  - [ ] 4.1 实现商品数据模型
    - 创建 Item、ItemSku、ItemBarcode、ItemCategory SQLAlchemy 模型
    - 创建对应的 Pydantic Schema
    - _需求: 1.1, 1.4_
  - [ ]* 4.2 编写属性测试：SKU_ID 全局唯一性
    - **属性 1: SKU_ID 全局唯一性**
    - 使用 Hypothesis 生成测试数据
    - **验证: 需求 1.1**
  - [ ] 4.3 实现 SKU_ID 生成服务
    - 实现 Redis + 本地缓存号段的 SKU_ID 生成器
    - _需求: 1.1_
  - [ ] 4.4 实现商品 CRUD 服务
    - 实现商品创建、查询、更新、删除
    - 实现条码关联功能
    - _需求: 1.1, 1.3, 1.4_
  - [ ] 4.5 实现商品事件发布
    - 实现 ItemCreated、ItemUpdated 事件发布到 Kafka
    - _需求: 1.2, 1.3_
  - [ ] 4.6 实现商品 REST API
    - 实现 POST /item/create
    - 实现 GET /item/{id}
    - 实现 GET /item/list
    - 实现 GET /item/barcode/{code}
    - _需求: 1.5_
  - [ ]* 4.7 编写商品服务单元测试
    - 使用 pytest-asyncio 测试异步接口
    - 测试商品创建、查询、更新功能
    - 测试条码关联功能
    - _需求: 1.1, 1.4_

- [ ] 5. 检查点 - 确保所有测试通过

- [ ] 6. 用户中心 (user_service)
  - [ ] 6.1 实现用户数据模型
    - 创建 User、UserRole、Org、Role、Permission SQLAlchemy 模型
    - 创建对应的 Pydantic Schema
    - _需求: 2.1, 2.3, 2.4_
  - [ ] 6.2 实现用户认证服务
    - 实现密码加密（passlib + bcrypt）
    - 实现 JWT Token 生成和验证（python-jose）
    - 实现登录接口
    - _需求: 2.2_
  - [ ]* 6.3 编写属性测试：认证令牌有效性验证
    - **属性 13: 认证令牌有效性验证**
    - **验证: 需求 14.1, 14.2**
  - [ ] 6.4 实现角色权限服务
    - 实现角色分配功能
    - 实现权限查询功能
    - 实现 FastAPI 依赖注入权限校验
    - _需求: 2.3, 2.5_
  - [ ] 6.5 实现用户事件发布
    - 实现 UserCreated、UserUpdated 事件发布
    - _需求: 2.1_
  - [ ] 6.6 实现用户 REST API
    - 实现 POST /user/login
    - 实现 POST /user/create
    - 实现 GET /user/{id}
    - 实现 POST /user/role/assign
    - _需求: 2.1, 2.2, 2.3_
  - [ ]* 6.7 编写用户服务单元测试
    - 测试用户创建、登录、角色分配功能
    - _需求: 2.1, 2.2, 2.3_

- [ ] 7. 检查点 - 确保所有测试通过

- [ ] 8. 库存中心 (stock_service)
  - [ ] 8.1 实现库存数据模型
    - 创建 Stock、StockDetail、StockMove SQLAlchemy 模型
    - 创建对应的 Pydantic Schema
    - _需求: 6.1, 6.3, 6.6_
  - [ ] 8.2 实现库存入库服务
    - 实现入库操作，更新 stock 表和 stock_move 表
    - 使用 SQLAlchemy 异步事务
    - _需求: 6.1_
  - [ ]* 8.3 编写属性测试：库存数量守恒
    - **属性 2: 库存数量守恒**
    - **验证: 需求 6.1, 6.3**
  - [ ] 8.4 实现库存出库服务
    - 实现出库操作，更新 stock 表和 stock_move 表
    - _需求: 6.3_
  - [ ] 8.5 实现库存锁定服务
    - 实现库存锁定和解锁功能
    - 使用 Redis 分布式锁保证并发安全
    - _需求: 6.6, 6.7_
  - [ ]* 8.6 编写属性测试：可用库存计算正确性
    - **属性 3: 可用库存计算正确性**
    - **验证: 需求 6.7**
  - [ ] 8.7 实现库存事件发布
    - 实现 StockIn、StockOut、StockChanged 事件发布
    - _需求: 6.2, 6.4, 6.5_
  - [ ]* 8.8 编写属性测试：事件内容完整性
    - **属性 14: 事件内容完整性**
    - **验证: 需求 12.4**
  - [ ] 8.9 实现库存 REST API
    - 实现 POST /stock/in
    - 实现 POST /stock/out
    - 实现 POST /stock/lock
    - 实现 POST /stock/unlock
    - 实现 GET /stock/{sku_id}
    - _需求: 6.1, 6.3, 6.6_
  - [ ]* 8.10 编写库存服务单元测试
    - 测试入库、出库、锁定、解锁功能
    - _需求: 6.1, 6.3, 6.6_

- [ ] 9. 检查点 - 确保所有测试通过

---

## 第三阶段：业务服务实现

- [ ] 10. 采购中心 (purchase_service)
  - [ ] 10.1 实现采购数据模型
    - 创建 PoOrder、PoDetail、Supplier SQLAlchemy 模型
    - _需求: 3.1, 3.5_
  - [ ] 10.2 实现采购订单服务
    - 实现采购订单创建、审批、收货功能
    - _需求: 3.1, 3.2, 3.3_
  - [ ] 10.3 实现采购入库集成
    - 使用 httpx 异步调用库存中心 /stock/in API
    - _需求: 3.3_
  - [ ] 10.4 实现采购事件发布
    - 实现 PoApproved、PoInStock 事件发布
    - _需求: 3.2, 3.4_
  - [ ] 10.5 实现采购 REST API
    - 实现 /po/create、/po/{id}、/po/approve、/po/receive
    - _需求: 3.1, 3.2, 3.3_
  - [ ]* 10.6 编写采购服务单元测试
    - _需求: 3.1, 3.2, 3.3_

- [ ] 11. 生产中心 (production_service)
  - [ ] 11.1 实现生产数据模型
    - 创建 MoOrder、MoBom、MoRouting、BomTemplate SQLAlchemy 模型
    - _需求: 4.1, 4.4, 4.5_
  - [ ] 11.2 实现生产订单服务
    - 实现生产订单创建、下达、开始功能
    - _需求: 4.1, 4.2_
  - [ ] 11.3 实现 BOM 管理服务
    - 实现 BOM 模板创建、复制到生产订单功能
    - _需求: 4.4_
  - [ ] 11.4 实现生产事件发布
    - 实现 MoStarted 事件发布
    - _需求: 4.2_
  - [ ] 11.5 实现库存领料事件消费
    - 使用 aiokafka 监听 MoStarted 事件
    - 调用库存中心扣料
    - _需求: 4.3_
  - [ ]* 11.6 编写属性测试：BOM 领料数量正确性
    - **属性 6: BOM 领料数量正确性**
    - **验证: 需求 4.3**
  - [ ] 11.7 实现生产 REST API
    - 实现 /mo/create、/mo/{id}、/mo/start、/mo/bom
    - _需求: 4.1, 4.2, 4.4_
  - [ ]* 11.8 编写生产服务单元测试
    - _需求: 4.1, 4.4_

- [ ] 12. 检查点 - 确保所有测试通过

- [ ] 13. 报工中心 (job_service)
  - [ ] 13.1 实现报工数据模型
    - 创建 ReportJob、ReportLoss SQLAlchemy 模型
    - _需求: 5.1, 5.3_
  - [ ] 13.2 实现报工服务
    - 实现扫码报工功能
    - 实现报工数量校验（异常检测）
    - _需求: 5.1, 5.5_
  - [ ]* 13.3 编写属性测试：报工数量异常检测
    - **属性 15: 报工数量异常检测**
    - **验证: 需求 5.5**
  - [ ] 13.4 实现损耗记录服务
    - _需求: 5.3_
  - [ ] 13.5 实现报工事件发布
    - 实现 JobReported、MoCompleted 事件发布
    - _需求: 5.2, 5.4_
  - [ ] 13.6 实现报工 REST API
    - 实现 /job/report、/job/loss、/job/{mo_id}/status
    - _需求: 5.1, 5.3_
  - [ ]* 13.7 编写报工服务单元测试
    - _需求: 5.1, 5.3_

- [ ] 14. 成本中心 (cost_service)
  - [ ] 14.1 实现成本数据模型
    - 创建 CostSheet、CostItem SQLAlchemy 模型
    - _需求: 7.3_
  - [ ] 14.2 实现成本计算服务
    - 实现移动加权平均法计算采购成本
    - 实现标准成本法计算生产成本
    - _需求: 7.1, 7.2, 7.5_
  - [ ]* 14.3 编写属性测试：成本计算触发完整性
    - **属性 7: 成本计算触发完整性**
    - **验证: 需求 7.1, 7.2**
  - [ ] 14.4 实现成本事件消费
    - 监听 StockChanged、MoCompleted 事件触发成本计算
    - _需求: 7.1, 7.2_
  - [ ] 14.5 实现成本事件发布
    - 实现 CostCalculated 事件发布
    - _需求: 7.3_
  - [ ] 14.6 实现成本 REST API
    - 实现 /cost/{sku_id}、/cost/list、/cost/calculate
    - _需求: 7.4_
  - [ ]* 14.7 编写成本服务单元测试
    - _需求: 7.1, 7.2_

- [ ] 15. 检查点 - 确保所有测试通过

- [ ] 16. 订单中心 (order_service)
  - [ ] 16.1 实现订单数据模型
    - 创建 SoOrder、SoDetail、Payment SQLAlchemy 模型
    - _需求: 8.1_
  - [ ] 16.2 实现订单号生成服务
    - 实现订单号生成规则（渠道+门店+日期+序列号）
    - _需求: 8.1_
  - [ ] 16.3 实现订单创建服务
    - 调用促销中心算价
    - 调用库存中心锁定库存
    - 创建订单记录
    - _需求: 8.1, 8.2, 8.6_
  - [ ]* 16.4 编写属性测试：订单-库存锁定一致性
    - **属性 4: 订单-库存锁定一致性**
    - **验证: 需求 8.2**
  - [ ] 16.5 实现订单支付服务
    - 实现支付记录创建
    - 发布 OrderPaid 事件
    - _需求: 8.3_
  - [ ]* 16.6 编写属性测试：支付-出库联动正确性
    - **属性 5: 支付-出库联动正确性**
    - **验证: 需求 8.4**
  - [ ] 16.7 实现订单发货服务
    - 实现发货状态更新
    - 发布 OrderShipped 事件
    - _需求: 8.5_
  - [ ] 16.8 实现库存出库事件消费
    - 监听 OrderPaid 事件，调用库存中心出库
    - _需求: 8.4_
  - [ ] 16.9 实现订单 REST API
    - 实现 /order/create、/order/{id}、/order/pay、/order/ship
    - _需求: 8.1, 8.3, 8.5_
  - [ ]* 16.10 编写订单服务单元测试
    - _需求: 8.1, 8.3, 8.5_

- [ ] 17. 检查点 - 确保所有测试通过

- [ ] 18. 会员中心 (member_service)
  - [ ] 18.1 实现会员数据模型
    - 创建 Member、MemberPoint、MemberCoupon SQLAlchemy 模型
    - _需求: 9.1, 9.2, 9.3_
  - [ ] 18.2 实现会员注册服务
    - _需求: 9.1_
  - [ ] 18.3 实现积分变动服务
    - 实现积分增加、扣减、过期功能
    - _需求: 9.2, 9.4_
  - [ ]* 18.4 编写属性测试：会员积分变动一致性
    - **属性 10: 会员积分变动一致性**
    - **验证: 需求 9.2**
  - [ ] 18.5 实现会员等级服务
    - 实现等级自动调整功能
    - _需求: 9.5_
  - [ ]* 18.6 编写属性测试：会员等级自动调整正确性
    - **属性 11: 会员等级自动调整正确性**
    - **验证: 需求 9.5**
  - [ ] 18.7 实现优惠券服务
    - 实现优惠券发放、使用、过期功能
    - _需求: 9.3_
  - [ ] 18.8 实现会员事件发布
    - 实现 MemberPointChanged 事件发布
    - _需求: 9.2_
  - [ ] 18.9 实现会员 REST API
    - 实现 /member/register、/member/{id}、/member/point/change、/member/coupon
    - _需求: 9.1, 9.2, 9.3, 9.4_
  - [ ]* 18.10 编写会员服务单元测试
    - _需求: 9.1, 9.2, 9.5_

- [ ] 19. 促销中心 (promo_service)
  - [ ] 19.1 实现促销数据模型
    - 创建 Promo、PromoRule、PromoRecord SQLAlchemy 模型
    - _需求: 10.1_
  - [ ] 19.2 实现促销活动服务
    - 实现促销活动创建、启用、停用功能
    - _需求: 10.1_
  - [ ] 19.3 实现促销算价服务
    - 实现满减、折扣、买赠、特价、组合等促销类型计算
    - 实现最优促销选择逻辑
    - _需求: 10.2, 10.5_
  - [ ]* 19.4 编写属性测试：促销算价最优性
    - **属性 8: 促销算价最优性**
    - **验证: 需求 10.5**
  - [ ]* 19.5 编写属性测试：促销有效期约束
    - **属性 9: 促销有效期约束**
    - **验证: 需求 10.4**
  - [ ] 19.6 实现促销记录服务
    - 实现促销应用记录功能
    - _需求: 10.3_
  - [ ] 19.7 实现促销事件发布
    - 实现 PromoApplied 事件发布
    - _需求: 10.3_
  - [ ] 19.8 实现促销 REST API
    - 实现 /promo/calc、/promo/create、/promo/{id}、/promo/list
    - _需求: 10.1, 10.2_
  - [ ]* 19.9 编写促销服务单元测试
    - _需求: 10.1, 10.2_

- [ ] 20. 检查点 - 确保所有测试通过

---

## 第四阶段：网关与集成

- [ ] 21. Nginx 网关完善
  - [ ] 21.1 配置 JWT 认证 (lua-resty-jwt 或转发到 user_service)
    - 配置 Token 验证逻辑
    - 配置白名单路由
    - _需求: 14.1, 14.2_
  - [ ] 21.2 配置负载均衡
    - 配置各服务的健康检查
    - 配置权重和故障转移
    - _需求: 14.5_
  - [ ] 21.3 配置 POS 同步端点
    - 实现离线订单同步接口
    - _需求: 14.4_
  - [ ]* 21.4 编写网关集成测试
    - 测试认证、路由、限流功能
    - _需求: 14.1, 14.3, 14.5_

- [ ] 22. Kafka 事件总线集成
  - [ ] 22.1 配置 Kafka 生产者
    - 创建公共 KafkaProducer 类
    - 配置各服务的 Topic
    - _需求: 12.1_
  - [ ] 22.2 配置 Kafka 消费者
    - 创建公共 KafkaConsumer 基类
    - 实现消费失败重试和死信队列
    - 使用 asyncio 后台任务运行消费者
    - _需求: 12.3_
  - [ ] 22.3 实现事件消费集成
    - 库存中心消费 MoStarted、OrderPaid 事件
    - 成本中心消费 StockChanged、MoCompleted 事件
    - _需求: 4.3, 7.1, 7.2, 8.4_
  - [ ]* 22.4 编写事件集成测试
    - 测试事件发布和消费流程
    - _需求: 12.1, 12.3_

- [ ] 23. POS 离线同步
  - [ ] 23.1 实现离线订单同步服务
    - 实现离线订单接收和处理
    - 实现同步顺序校验
    - _需求: 11.2, 11.3_
  - [ ]* 23.2 编写属性测试：离线订单同步顺序性
    - **属性 12: 离线订单同步顺序性**
    - **验证: 需求 11.3**
  - [ ] 23.3 实现同步失败处理
    - 实现失败记录和重试机制
    - _需求: 11.4_
  - [ ]* 23.4 编写离线同步单元测试
    - _需求: 11.2, 11.3, 11.4_

- [ ] 24. 最终检查点 - 确保所有测试通过

---

## 第五阶段：端到端测试与部署

- [ ] 25. 核心业务流程测试
  - [ ]* 25.1 POS 开单链路测试
    - 测试完整的 POS 开单流程：算价→创建订单→锁库存→支付→出库
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.6, 10.2_
  - [ ]* 25.2 生产领料链路测试
    - 测试完整的生产领料流程：创建MO→开始生产→扣料→报工→完工→算成本
    - _需求: 4.1, 4.2, 4.3, 5.1, 5.4, 7.2_
  - [ ]* 25.3 采购入库链路测试
    - 测试完整的采购入库流程：创建PO→审批→收货→入库→算成本
    - _需求: 3.1, 3.2, 3.3, 3.4, 7.1_

- [ ] 26. Docker 容器化部署
  - [ ] 26.1 编写各服务 Dockerfile
    - 基于 python:3.11-slim 镜像
    - 多阶段构建优化镜像大小
  - [ ] 26.2 编写 docker-compose.yml
    - 配置所有服务、Nginx、Kafka、Redis、MySQL
    - 配置网络和数据卷
  - [ ] 26.3 编写启动脚本
    - 数据库迁移脚本
    - 服务健康检查脚本

---

## 附录：项目目录结构

```
erp-python/
├── pyproject.toml              # 项目依赖管理
├── docker-compose.yml          # Docker 编排
├── alembic.ini                 # 数据库迁移配置
├── nginx/
│   ├── nginx.conf              # Nginx 主配置
│   └── conf.d/
│       └── upstream.conf       # 服务路由配置
├── erp_common/                 # 公共模块
│   ├── __init__.py
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── schemas/
│   │   ├── base.py             # Result[T], PageQuery, PageResult
│   │   └── events.py           # DomainEvent 基类
│   ├── utils/
│   │   ├── jwt_utils.py        # JWT 工具
│   │   ├── redis_utils.py      # Redis 工具
│   │   └── kafka_utils.py      # Kafka 生产者/消费者
│   └── exceptions.py           # 统一异常定义
├── services/
│   ├── item_service/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── models.py           # SQLAlchemy 模型
│   │   ├── schemas.py          # Pydantic Schema
│   │   ├── service.py          # 业务逻辑
│   │   ├── repository.py       # 数据访问层
│   │   └── api.py              # API 路由
│   ├── user_service/
│   ├── stock_service/
│   ├── purchase_service/
│   ├── production_service/
│   ├── job_service/
│   ├── cost_service/
│   ├── order_service/
│   ├── member_service/
│   └── promo_service/
├── migrations/                 # Alembic 迁移文件
│   └── versions/
├── tests/
│   ├── conftest.py             # pytest 配置
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   └── e2e/                    # 端到端测试
└── scripts/
    ├── init_db.py              # 数据库初始化
    └── start_services.sh       # 服务启动脚本
```

---

## 附录：核心依赖清单 (pyproject.toml)

```toml
[project]
name = "erp-system"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    # Web 框架
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "httpx>=0.26.0",
    
    # 数据库
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",           # PostgreSQL 异步驱动
    "aiomysql>=0.2.0",           # MySQL 异步驱动
    "alembic>=1.13.0",
    
    # 数据校验
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    
    # 认证
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    
    # 消息队列
    "aiokafka>=0.10.0",
    
    # 缓存
    "redis>=5.0.0",
    
    # 工具
    "python-multipart>=0.0.6",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "hypothesis>=6.92.0",
    "httpx>=0.26.0",
]
```
