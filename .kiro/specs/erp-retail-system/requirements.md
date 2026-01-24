# 需求文档

## 简介

本文档定义了一套 SaaS ERP/零售混合系统的功能需求。该系统采用微服务架构，包含商品、订单、采购、生产、库存、报工、成本、用户、会员、促销等核心模块，支持门店 POS、小程序、管理后台等多端接入。

## 术语表

- **ERP_System**: ERP/零售混合系统，本文档描述的目标系统
- **SKU**: Stock Keeping Unit，库存单位，商品的最小管理单元
- **POS**: Point of Sale，销售终端，门店收银系统
- **MO**: Manufacturing Order，生产订单
- **PO**: Purchase Order，采购订单
- **SO**: Sales Order，销售订单
- **BOM**: Bill of Materials，物料清单
- **Item_Service**: 商品中心微服务
- **User_Service**: 用户中心微服务
- **Purchase_Service**: 采购中心微服务
- **Production_Service**: 生产中心微服务
- **Job_Service**: 报工中心微服务
- **Stock_Service**: 库存中心微服务
- **Cost_Service**: 成本中心微服务
- **Order_Service**: 订单中心微服务
- **Member_Service**: 会员中心微服务
- **Promo_Service**: 促销中心微服务
- **Event_Bus**: 事件总线，基于 Kafka 的异步消息系统

## 需求

### 需求 1：商品管理

**用户故事：** 作为商品管理员，我希望能够管理商品主档信息，以便统一维护全系统的商品数据。

#### 验收标准

1. WHEN 管理员创建新商品 THEN Item_Service SHALL 生成全局唯一的 SKU_ID 并存储商品信息到 item 表
2. WHEN 商品创建成功 THEN Item_Service SHALL 发布 ItemCreated 事件到 Event_Bus
3. WHEN 管理员更新商品信息 THEN Item_Service SHALL 更新 item 表并发布 ItemUpdated 事件
4. WHEN 管理员为商品添加条码 THEN Item_Service SHALL 在 item_barcode 表中关联条码与 SKU_ID
5. WHEN 其他服务需要商品信息 THEN 该服务 SHALL 通过 /item/* API 查询，禁止直接访问 item 表

### 需求 2：用户与组织管理

**用户故事：** 作为系统管理员，我希望能够统一管理用户、角色和组织，以便实现统一登录和权限控制。

#### 验收标准

1. WHEN 管理员创建用户 THEN User_Service SHALL 在 user 表中创建记录并发布 UserCreated 事件
2. WHEN 用户登录系统 THEN User_Service SHALL 验证凭据并返回包含角色信息的认证令牌
3. WHEN 管理员分配角色 THEN User_Service SHALL 在 user_role 表中建立用户与角色的关联
4. WHEN 管理员创建组织（门店/供应商） THEN User_Service SHALL 在 org 表中创建组织记录
5. WHILE 用户会话有效 THEN ERP_System SHALL 允许用户访问其角色授权的功能

### 需求 3：采购管理

**用户故事：** 作为采购员，我希望能够创建和管理采购订单，以便完成商品采购流程。

#### 验收标准

1. WHEN 采购员创建采购订单 THEN Purchase_Service SHALL 在 po_order 和 po_detail 表中创建记录
2. WHEN 采购订单审批通过 THEN Purchase_Service SHALL 发布 PoApproved 事件
3. WHEN 仓库确认收货 THEN Purchase_Service SHALL 调用 Stock_Service /stock/in API 执行入库
4. WHEN 入库完成 THEN Purchase_Service SHALL 发布 PoInStock 事件
5. WHEN 管理员维护供应商 THEN Purchase_Service SHALL 在 supplier 表中管理供应商信息

### 需求 4：生产管理

**用户故事：** 作为生产计划员，我希望能够创建和管理生产订单，以便安排生产任务。

#### 验收标准

1. WHEN 计划员创建生产订单 THEN Production_Service SHALL 在 mo_order 表中创建记录并关联 BOM
2. WHEN 生产订单开始执行 THEN Production_Service SHALL 发布 MoStarted 事件
3. WHEN Stock_Service 收到 MoStarted 事件 THEN Stock_Service SHALL 根据 BOM 自动扣减原材料库存
4. WHEN 计划员维护 BOM THEN Production_Service SHALL 在 mo_bom 表中管理物料清单
5. WHEN 计划员维护工艺路线 THEN Production_Service SHALL 在 mo_routing 表中管理工序信息

### 需求 5：报工管理

**用户故事：** 作为生产工人，我希望能够通过扫码报工，以便记录生产进度和完工情况。

#### 验收标准

1. WHEN 工人扫码报工 THEN Job_Service SHALL 在 report_job 表中创建报工记录
2. WHEN 报工记录创建成功 THEN Job_Service SHALL 发布 JobReported 事件
3. WHEN 工人报告损耗 THEN Job_Service SHALL 在 report_loss 表中记录损耗信息
4. WHEN 生产订单所有工序完工 THEN Job_Service SHALL 发布 MoCompleted 事件
5. IF 报工数据异常（如超出计划数量） THEN Job_Service SHALL 标记异常并通知相关人员

### 需求 6：库存管理

**用户故事：** 作为仓库管理员，我希望能够管理库存的入库、出库和调拨，以便准确掌握实物库存。

#### 验收标准

1. WHEN 执行入库操作 THEN Stock_Service SHALL 更新 stock 表数量并在 stock_move 表记录流水
2. WHEN 入库完成 THEN Stock_Service SHALL 发布 StockIn 事件
3. WHEN 执行出库操作 THEN Stock_Service SHALL 更新 stock 表数量并在 stock_move 表记录流水
4. WHEN 出库完成 THEN Stock_Service SHALL 发布 StockOut 事件
5. WHEN 库存数量变化 THEN Stock_Service SHALL 发布 StockChanged 事件
6. WHEN Order_Service 请求锁定库存 THEN Stock_Service SHALL 在 stock_detail 表中标记锁定数量
7. WHILE 库存被锁定 THEN Stock_Service SHALL 在可用库存计算中排除锁定数量

### 需求 7：成本核算

**用户故事：** 作为财务人员，我希望系统能够自动计算商品成本，以便准确核算利润。

#### 验收标准

1. WHEN Cost_Service 收到 StockChanged 事件 THEN Cost_Service SHALL 重新计算相关 SKU 的成本
2. WHEN Cost_Service 收到 MoCompleted 事件 THEN Cost_Service SHALL 计算生产成本并分摊到成品
3. WHEN 成本计算完成 THEN Cost_Service SHALL 在 cost_sheet 表中记录并发布 CostCalculated 事件
4. WHEN 其他服务需要成本数据 THEN 该服务 SHALL 通过 /cost/* API 查询，禁止直接写入 cost_sheet 表
5. WHILE 执行月结 THEN Cost_Service SHALL 按加权平均法或移动平均法计算期末成本

### 需求 8：销售订单管理

**用户故事：** 作为销售人员，我希望能够创建和管理销售订单，以便完成销售流程。

#### 验收标准

1. WHEN 用户提交订单 THEN Order_Service SHALL 在 so_order 和 so_detail 表中创建记录
2. WHEN 订单创建时 THEN Order_Service SHALL 调用 Stock_Service /stock/lock API 锁定库存
3. WHEN 订单支付成功 THEN Order_Service SHALL 发布 OrderPaid 事件
4. WHEN Stock_Service 收到 OrderPaid 事件 THEN Stock_Service SHALL 执行实际出库操作
5. WHEN 订单发货完成 THEN Order_Service SHALL 发布 OrderShipped 事件
6. WHEN 订单创建前 THEN Order_Service SHALL 调用 Promo_Service /promo/calc API 计算促销价格

### 需求 9：会员管理

**用户故事：** 作为会员运营人员，我希望能够管理会员信息和积分，以便提升会员忠诚度。

#### 验收标准

1. WHEN 顾客注册会员 THEN Member_Service SHALL 在 member 表中创建会员记录
2. WHEN 会员积分变动 THEN Member_Service SHALL 更新 member_point 表并发布 MemberPointChanged 事件
3. WHEN 系统发放优惠券 THEN Member_Service SHALL 在 member_coupon 表中创建记录
4. WHEN 其他服务需要变更积分 THEN 该服务 SHALL 调用 /member/point/change API
5. WHILE 会员等级规则生效 THEN Member_Service SHALL 根据消费金额自动调整会员等级

### 需求 10：促销管理

**用户故事：** 作为营销人员，我希望能够配置促销活动，以便吸引顾客购买。

#### 验收标准

1. WHEN 营销人员创建促销活动 THEN Promo_Service SHALL 在 promo 和 promo_rule 表中创建记录
2. WHEN POS 或小程序请求算价 THEN Promo_Service SHALL 根据 promo_rule 计算最优价格并返回
3. WHEN 促销被应用 THEN Promo_Service SHALL 在 promo_record 表中记录并发布 PromoApplied 事件
4. WHILE 促销活动有效期内 THEN Promo_Service SHALL 在算价时应用该促销规则
5. IF 多个促销规则冲突 THEN Promo_Service SHALL 按优先级选择最优惠的规则

### 需求 11：POS 离线支持

**用户故事：** 作为门店收银员，我希望在网络断开时仍能继续收银，以便不影响门店正常营业。

#### 验收标准

1. WHILE POS 处于离线状态 THEN POS SHALL 将订单数据存储到本地 SQLite 数据库
2. WHEN POS 恢复网络连接 THEN POS SHALL 自动将离线订单同步到 Order_Service
3. WHEN 同步离线订单时 THEN POS SHALL 按订单创建时间顺序逐笔同步
4. IF 离线订单同步失败 THEN POS SHALL 记录失败原因并支持手动重试
5. WHILE POS 离线 THEN POS SHALL 使用本地缓存的商品和价格数据

### 需求 12：事件总线规范

**用户故事：** 作为系统架构师，我希望事件总线只传递业务事实，以便保证系统的一致性和可维护性。

#### 验收标准

1. WHEN 服务发布事件 THEN 该服务 SHALL 只发布"业务已发生"的事实，禁止发布指令
2. WHEN 服务需要触发其他服务操作 THEN 该服务 SHALL 通过同步 REST API 调用
3. WHEN 事件消费失败 THEN Event_Bus SHALL 支持消息重试和死信队列
4. WHEN 发布事件 THEN 该服务 SHALL 在事件中包含完整的业务上下文信息
5. WHILE 系统运行 THEN Event_Bus SHALL 保证事件的顺序性和至少一次投递

### 需求 13：数据归属与一致性

**用户故事：** 作为系统架构师，我希望明确数据归属，以便防止数据不一致问题。

#### 验收标准

1. WHEN 任何服务需要修改库存数量 THEN 该服务 SHALL 调用 Stock_Service API，禁止直接写 stock 表
2. WHEN 任何服务需要修改成本数据 THEN 该服务 SHALL 调用 Cost_Service API，禁止直接写 cost_sheet 表
3. WHEN 任何服务需要商品主档 THEN 该服务 SHALL 只存储 SKU_ID 外键，禁止复制商品数据
4. WHEN 任何服务需要修改会员积分 THEN 该服务 SHALL 调用 Member_Service API，禁止直接写 member_point 表
5. WHILE 系统运行 THEN ERP_System SHALL 保证实物库存与 stock 表数据一致

### 需求 14：API 网关

**用户故事：** 作为系统架构师，我希望有统一的 API 网关，以便实现统一鉴权和流量控制。

#### 验收标准

1. WHEN 客户端请求到达 THEN API_Gateway SHALL 验证认证令牌的有效性
2. WHEN 认证失败 THEN API_Gateway SHALL 返回 401 状态码并拒绝请求
3. WHILE 系统运行 THEN API_Gateway SHALL 对各服务 API 实施限流保护
4. WHEN POS 离线订单同步 THEN API_Gateway SHALL 提供专用的同步端点
5. WHEN 请求通过认证 THEN API_Gateway SHALL 将请求路由到对应的微服务
