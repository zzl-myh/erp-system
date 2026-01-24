# 设计文档

## 概述

本设计文档描述 ERP/零售混合系统的技术架构和实现方案。系统采用微服务架构，包含 10 个核心服务，通过 Kafka 事件总线实现异步通信，通过 REST API 实现同步调用。

## 架构

### 整体架构图

```mermaid
graph TB
    subgraph 客户端层
        MP[小程序]
        POS[门店POS]
        ADMIN[管理后台]
    end
    
    subgraph 网关层
        GW[Nginx<br/>反向代理/限流/路由]
    end
    
    subgraph 服务层
        ITEM["① 商品中心<br/>FastAPI"]
        USER["② 用户中心<br/>FastAPI"]
        PO["③ 采购中心<br/>FastAPI"]
        MO["④ 生产中心<br/>FastAPI"]
        JOB["⑤ 报工中心<br/>FastAPI"]
        STOCK["⑥ 库存中心<br/>FastAPI"]
        COST["⑦ 成本中心<br/>FastAPI"]
        ORDER["⑧ 订单中心<br/>FastAPI"]
        MEMBER["⑨ 会员中心<br/>FastAPI"]
        PROMO["⑩ 促销中心<br/>FastAPI"]
    end
    
    subgraph 消息层
        KAFKA[Kafka 事件总线]
    end
    
    subgraph 数据层
        MYSQL[(MySQL 主库)]
        STOCK_DB[(库存分库)]
        BI_DB[(BI 读库)]
    end
    
    MP --> GW
    POS --> GW
    ADMIN --> GW
    
    GW --> ITEM
    GW --> USER
    GW --> PO
    GW --> MO
    GW --> JOB
    GW --> STOCK
    GW --> COST
    GW --> ORDER
    GW --> MEMBER
    GW --> PROMO
    
    ITEM --> KAFKA
    USER --> KAFKA
    PO --> KAFKA
    MO --> KAFKA
    JOB --> KAFKA
    STOCK --> KAFKA
    COST --> KAFKA
    ORDER --> KAFKA
    MEMBER --> KAFKA
    PROMO --> KAFKA
    
    ITEM --> MYSQL
    USER --> MYSQL
    PO --> MYSQL
    MO --> MYSQL
    JOB --> MYSQL
    COST --> MYSQL
    ORDER --> MYSQL
    MEMBER --> MYSQL
    PROMO --> MYSQL
    STOCK --> STOCK_DB
    
    MYSQL --> BI_DB
    STOCK_DB --> BI_DB
```

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3 + ElementUI Plus |
| 小程序 | UniAPP |
| POS | Electron + Vue + SQLite |
| 网关 | **Nginx** (反向代理/负载均衡/限流) |
| 服务 | **FastAPI + Uvicorn** |
| ORM | **SQLAlchemy 2.0 (异步)** |
| 数据校验 | **Pydantic v2** |
| 消息 | Apache Kafka (**aiokafka**) |
| 数据库 | MySQL 8.0 (**aiomysql**) |
| 缓存 | Redis (**aioredis**) |
| 认证 | **JWT (python-jose)** |
| 配置中心 | Consul / 环境变量 |
| 测试框架 | **pytest + Hypothesis** |

## 组件与接口

### 服务间调用关系

```mermaid
sequenceDiagram
    participant POS as POS终端
    participant GW as Nginx网关
    participant PROMO as 促销中心
    participant ORDER as 订单中心
    participant STOCK as 库存中心
    participant KAFKA as Kafka
    participant COST as 成本中心
    
    POS->>GW: 1. 请求算价
    GW->>PROMO: /promo/calc
    PROMO-->>POS: 返回促销价格
    
    POS->>GW: 2. 创建订单
    GW->>ORDER: /order/create
    ORDER->>STOCK: /stock/lock (锁库存)
    STOCK-->>ORDER: 锁定成功
    ORDER-->>POS: 订单创建成功
    
    POS->>GW: 3. 支付完成
    GW->>ORDER: /order/pay
    ORDER->>KAFKA: OrderPaid 事件
    KAFKA->>STOCK: 消费 OrderPaid
    STOCK->>STOCK: 执行出库
    STOCK->>KAFKA: StockOut 事件
    KAFKA->>COST: 消费 StockOut
    COST->>COST: 重算成本
```

### 核心 API 接口

#### 商品中心 (item_service)

| 接口 | 方法 | 描述 |
|------|------|------|
| /item/create | POST | 创建商品 |
| /item/{id} | GET | 查询商品详情 |
| /item/{id} | PUT | 更新商品信息 |
| /item/list | GET | 商品列表查询 |
| /item/barcode/{code} | GET | 按条码查询商品 |

#### 库存中心 (stock_service)

| 接口 | 方法 | 描述 |
|------|------|------|
| /stock/in | POST | 入库操作 |
| /stock/out | POST | 出库操作 |
| /stock/lock | POST | 锁定库存 |
| /stock/unlock | POST | 解锁库存 |
| /stock/{sku_id} | GET | 查询库存 |
| /stock/move/list | GET | 库存流水查询 |

#### 订单中心 (order_service)

| 接口 | 方法 | 描述 |
|------|------|------|
| /order/create | POST | 创建订单 |
| /order/{id} | GET | 查询订单详情 |
| /order/pay | POST | 订单支付 |
| /order/ship | POST | 订单发货 |
| /order/list | GET | 订单列表查询 |

#### 促销中心 (promo_service)

| 接口 | 方法 | 描述 |
|------|------|------|
| /promo/calc | POST | 计算促销价格 |
| /promo/create | POST | 创建促销活动 |
| /promo/{id} | GET | 查询促销详情 |
| /promo/list | GET | 促销活动列表 |

### 事件定义

| 事件名称 | 发布服务 | 消费服务 | 触发场景 |
|----------|----------|----------|----------|
| ItemCreated | 商品中心 | - | 商品创建成功 |
| ItemUpdated | 商品中心 | - | 商品信息更新 |
| UserCreated | 用户中心 | - | 用户创建成功 |
| PoApproved | 采购中心 | - | 采购订单审批通过 |
| PoInStock | 采购中心 | 成本中心 | 采购入库完成 |
| MoStarted | 生产中心 | 库存中心 | 生产订单开始 |
| MoCompleted | 报工中心 | 成本中心 | 生产订单完工 |
| JobReported | 报工中心 | - | 报工记录创建 |
| StockIn | 库存中心 | 成本中心 | 入库完成 |
| StockOut | 库存中心 | 成本中心 | 出库完成 |
| StockChanged | 库存中心 | 成本中心 | 库存数量变化 |
| CostCalculated | 成本中心 | - | 成本计算完成 |
| OrderPaid | 订单中心 | 库存中心、会员中心 | 订单支付成功 |
| OrderShipped | 订单中心 | - | 订单发货完成 |
| MemberPointChanged | 会员中心 | - | 会员积分变动 |
| PromoApplied | 促销中心 | - | 促销规则应用 |

## 数据模型

### 商品中心

```sql
-- 商品主表
CREATE TABLE item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) UNIQUE NOT NULL COMMENT '全局唯一SKU编码',
    name VARCHAR(200) NOT NULL COMMENT '商品名称',
    category_id BIGINT COMMENT '分类ID',
    unit VARCHAR(20) COMMENT '计量单位',
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0停用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 商品SKU表
CREATE TABLE item_sku (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    item_id BIGINT NOT NULL,
    sku_id VARCHAR(32) UNIQUE NOT NULL,
    spec_info JSON COMMENT '规格信息',
    price DECIMAL(10,2) COMMENT '销售价',
    cost DECIMAL(10,2) COMMENT '成本价',
    FOREIGN KEY (item_id) REFERENCES item(id)
);

-- 商品条码表
CREATE TABLE item_barcode (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    barcode VARCHAR(50) NOT NULL,
    is_primary TINYINT DEFAULT 0 COMMENT '是否主条码',
    UNIQUE KEY uk_barcode (barcode)
);

-- 商品分类表
CREATE TABLE item_category (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    parent_id BIGINT DEFAULT 0,
    level INT DEFAULT 1,
    sort_order INT DEFAULT 0
);
```

### 库存中心

```sql
-- 库存主表
CREATE TABLE stock (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    warehouse_id BIGINT NOT NULL COMMENT '仓库ID',
    quantity DECIMAL(10,2) DEFAULT 0 COMMENT '实际库存',
    locked_qty DECIMAL(10,2) DEFAULT 0 COMMENT '锁定数量',
    available_qty DECIMAL(10,2) GENERATED ALWAYS AS (quantity - locked_qty) STORED COMMENT '可用库存',
    UNIQUE KEY uk_sku_wh (sku_id, warehouse_id)
);

-- 库存明细表
CREATE TABLE stock_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    warehouse_id BIGINT NOT NULL,
    batch_no VARCHAR(50) COMMENT '批次号',
    quantity DECIMAL(10,2) DEFAULT 0,
    locked_qty DECIMAL(10,2) DEFAULT 0,
    cost DECIMAL(10,2) COMMENT '批次成本',
    expire_date DATE COMMENT '过期日期'
);

-- 库存流水表
CREATE TABLE stock_move (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    warehouse_id BIGINT NOT NULL,
    move_type VARCHAR(20) NOT NULL COMMENT '类型: IN/OUT/LOCK/UNLOCK',
    quantity DECIMAL(10,2) NOT NULL,
    ref_type VARCHAR(20) COMMENT '关联单据类型',
    ref_id BIGINT COMMENT '关联单据ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 订单中心

```sql
-- 销售订单主表
CREATE TABLE so_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(32) UNIQUE NOT NULL,
    member_id BIGINT COMMENT '会员ID',
    store_id BIGINT COMMENT '门店ID',
    total_amount DECIMAL(10,2) NOT NULL COMMENT '订单总额',
    discount_amount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠金额',
    pay_amount DECIMAL(10,2) NOT NULL COMMENT '实付金额',
    status TINYINT DEFAULT 0 COMMENT '状态: 0待付款 1已付款 2已发货 3已完成 -1已取消',
    source VARCHAR(20) COMMENT '来源: POS/MP/WEB',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 销售订单明细表
CREATE TABLE so_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    sku_id VARCHAR(32) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    price DECIMAL(10,2) NOT NULL COMMENT '单价',
    discount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠',
    amount DECIMAL(10,2) NOT NULL COMMENT '小计',
    FOREIGN KEY (order_id) REFERENCES so_order(id)
);

-- 支付记录表
CREATE TABLE payment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    pay_method VARCHAR(20) NOT NULL COMMENT '支付方式',
    amount DECIMAL(10,2) NOT NULL,
    status TINYINT DEFAULT 0 COMMENT '状态: 0待支付 1成功 -1失败',
    pay_time DATETIME,
    FOREIGN KEY (order_id) REFERENCES so_order(id)
);
```

### 会员中心

```sql
-- 会员表
CREATE TABLE member (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mobile VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(50),
    level INT DEFAULT 1 COMMENT '会员等级',
    total_points INT DEFAULT 0 COMMENT '累计积分',
    available_points INT DEFAULT 0 COMMENT '可用积分',
    total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '累计消费',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 会员积分表
CREATE TABLE member_point (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    change_type VARCHAR(20) NOT NULL COMMENT '类型: EARN/USE/EXPIRE',
    points INT NOT NULL,
    ref_type VARCHAR(20) COMMENT '关联类型',
    ref_id BIGINT COMMENT '关联ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES member(id)
);

-- 会员优惠券表
CREATE TABLE member_coupon (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    coupon_id BIGINT NOT NULL,
    status TINYINT DEFAULT 0 COMMENT '状态: 0未使用 1已使用 -1已过期',
    use_time DATETIME,
    expire_time DATETIME NOT NULL,
    FOREIGN KEY (member_id) REFERENCES member(id)
);
```

### 促销中心

```sql
-- 促销活动表
CREATE TABLE promo (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL COMMENT '类型: DISCOUNT/GIFT/BUNDLE',
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0停用',
    priority INT DEFAULT 0 COMMENT '优先级'
);

-- 促销规则表
CREATE TABLE promo_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    promo_id BIGINT NOT NULL,
    rule_type VARCHAR(20) NOT NULL COMMENT '规则类型',
    condition_json JSON COMMENT '条件配置',
    action_json JSON COMMENT '动作配置',
    FOREIGN KEY (promo_id) REFERENCES promo(id)
);

-- 促销记录表
CREATE TABLE promo_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    promo_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 采购中心

```sql
-- 采购订单主表
CREATE TABLE po_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    po_no VARCHAR(32) UNIQUE NOT NULL,
    supplier_id BIGINT NOT NULL,
    warehouse_id BIGINT NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    status TINYINT DEFAULT 0 COMMENT '状态: 0草稿 1待审批 2已审批 3部分入库 4已入库 -1已取消',
    created_by BIGINT NOT NULL,
    approved_by BIGINT,
    approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 采购订单明细表
CREATE TABLE po_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    po_id BIGINT NOT NULL,
    sku_id VARCHAR(32) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    received_qty DECIMAL(10,2) DEFAULT 0 COMMENT '已入库数量',
    FOREIGN KEY (po_id) REFERENCES po_order(id)
);

-- 供应商表
CREATE TABLE supplier (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    contact VARCHAR(50),
    phone VARCHAR(20),
    address VARCHAR(500),
    status TINYINT DEFAULT 1
);
```

### 生产中心

```sql
-- 生产订单主表
CREATE TABLE mo_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_no VARCHAR(32) UNIQUE NOT NULL,
    sku_id VARCHAR(32) NOT NULL COMMENT '成品SKU',
    plan_qty DECIMAL(10,2) NOT NULL COMMENT '计划数量',
    completed_qty DECIMAL(10,2) DEFAULT 0 COMMENT '完工数量',
    warehouse_id BIGINT NOT NULL,
    status TINYINT DEFAULT 0 COMMENT '状态: 0草稿 1已下达 2生产中 3已完工 -1已取消',
    plan_start DATE,
    plan_end DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- BOM 物料清单表
CREATE TABLE mo_bom (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL,
    material_sku_id VARCHAR(32) NOT NULL COMMENT '原材料SKU',
    quantity DECIMAL(10,4) NOT NULL COMMENT '单位用量',
    issued_qty DECIMAL(10,2) DEFAULT 0 COMMENT '已领料数量',
    FOREIGN KEY (mo_id) REFERENCES mo_order(id)
);

-- 工艺路线表
CREATE TABLE mo_routing (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL,
    seq INT NOT NULL COMMENT '工序顺序',
    operation_name VARCHAR(100) NOT NULL COMMENT '工序名称',
    work_center VARCHAR(50) COMMENT '工作中心',
    std_hours DECIMAL(6,2) COMMENT '标准工时',
    FOREIGN KEY (mo_id) REFERENCES mo_order(id)
);
```

### 报工中心

```sql
-- 报工记录表
CREATE TABLE report_job (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL,
    routing_id BIGINT NOT NULL COMMENT '工序ID',
    worker_id BIGINT NOT NULL COMMENT '工人ID',
    quantity DECIMAL(10,2) NOT NULL COMMENT '报工数量',
    work_hours DECIMAL(6,2) COMMENT '实际工时',
    report_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TINYINT DEFAULT 1 COMMENT '状态: 1正常 0异常'
);

-- 损耗记录表
CREATE TABLE report_loss (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL,
    sku_id VARCHAR(32) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    reason VARCHAR(200),
    report_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 成本中心

```sql
-- 成本表
CREATE TABLE cost_sheet (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    period VARCHAR(7) NOT NULL COMMENT '期间: YYYY-MM',
    cost_type VARCHAR(20) NOT NULL COMMENT '类型: PURCHASE/PRODUCE',
    unit_cost DECIMAL(12,4) NOT NULL COMMENT '单位成本',
    total_qty DECIMAL(12,2) NOT NULL COMMENT '总数量',
    total_amount DECIMAL(14,2) NOT NULL COMMENT '总金额',
    calc_method VARCHAR(20) COMMENT '计算方法: WEIGHTED_AVG/MOVING_AVG',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sku_period (sku_id, period, cost_type)
);

-- 成本明细表
CREATE TABLE cost_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    cost_sheet_id BIGINT NOT NULL,
    ref_type VARCHAR(20) NOT NULL COMMENT '来源类型: PO/MO',
    ref_id BIGINT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cost_sheet_id) REFERENCES cost_sheet(id)
);
```

### 用户中心

```sql
-- 用户表
CREATE TABLE user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    name VARCHAR(50),
    mobile VARCHAR(20),
    email VARCHAR(100),
    org_id BIGINT COMMENT '所属组织',
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户角色关联表
CREATE TABLE user_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    role_code VARCHAR(50) NOT NULL,
    UNIQUE KEY uk_user_role (user_id, role_code)
);

-- 组织表
CREATE TABLE org (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(20) NOT NULL COMMENT '类型: STORE/WAREHOUSE/SUPPLIER/DEPT',
    parent_id BIGINT DEFAULT 0,
    status TINYINT DEFAULT 1
);

-- 角色表
CREATE TABLE role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500)
);

-- 权限表
CREATE TABLE permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    resource VARCHAR(200) COMMENT '资源路径',
    action VARCHAR(20) COMMENT '操作: READ/WRITE/DELETE'
);

-- 角色权限关联表
CREATE TABLE role_permission (
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);
```

## 正确性属性

*属性是指在系统所有有效执行中都应保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性是人类可读规范与机器可验证正确性保证之间的桥梁。*

### 属性 1：SKU_ID 全局唯一性
*对于任意*商品创建操作，生成的 SKU_ID 在整个系统中必须唯一，不与任何已存在的 SKU_ID 重复。
**验证: 需求 1.1**

### 属性 2：库存数量守恒
*对于任意*库存操作（入库/出库），操作后的库存数量变化必须等于操作数量，且 stock_move 表中的流水记录与实际变化一致。
**验证: 需求 6.1, 6.3**

### 属性 3：可用库存计算正确性
*对于任意*库存查询，可用库存 = 实际库存 - 锁定数量，且该值始终 >= 0。
**验证: 需求 6.7**

### 属性 4：订单-库存锁定一致性
*对于任意*订单创建操作，订单明细中的商品数量必须与库存锁定数量一致。
**验证: 需求 8.2**

### 属性 5：支付-出库联动正确性
*对于任意*订单支付成功事件，库存中心必须执行对应的出库操作，出库数量与订单数量一致。
**验证: 需求 8.4**

### 属性 6：BOM 领料数量正确性
*对于任意*生产订单开始事件，库存扣减数量必须等于 BOM 用量 × 生产数量。
**验证: 需求 4.3**

### 属性 7：成本计算触发完整性
*对于任意*库存变化事件或生产完工事件，成本中心必须重新计算相关 SKU 的成本。
**验证: 需求 7.1, 7.2**

### 属性 8：促销算价最优性
*对于任意*算价请求，当存在多个适用的促销规则时，返回的价格必须是所有规则中最优惠的。
**验证: 需求 10.5**

### 属性 9：促销有效期约束
*对于任意*算价请求，只有在有效期内的促销规则才会被应用。
**验证: 需求 10.4**

### 属性 10：会员积分变动一致性
*对于任意*积分变动操作，member_point 表的变动记录之和必须等于 member 表中 available_points 的变化。
**验证: 需求 9.2**

### 属性 11：会员等级自动调整正确性
*对于任意*会员，其等级必须与累计消费金额对应的等级规则一致。
**验证: 需求 9.5**

### 属性 12：离线订单同步顺序性
*对于任意*离线订单同步操作，订单必须按创建时间顺序同步，不得乱序。
**验证: 需求 11.3**

### 属性 13：认证令牌有效性验证
*对于任意*API 请求，无效或过期的认证令牌必须返回 401 状态码。
**验证: 需求 14.1, 14.2**

### 属性 14：事件内容完整性
*对于任意*发布的业务事件，必须包含完整的业务上下文信息（事件类型、时间戳、业务ID、操作数据）。
**验证: 需求 12.4**

### 属性 15：报工数量异常检测
*对于任意*报工操作，当报工数量超出计划数量时，系统必须标记异常状态。
**验证: 需求 5.5**

## 错误处理

### 错误码规范

| 错误码 | 描述 | 处理方式 |
|--------|------|----------|
| 400 | 请求参数错误 | 返回具体字段错误信息 |
| 401 | 认证失败 | 引导重新登录 |
| 403 | 权限不足 | 提示无权限 |
| 404 | 资源不存在 | 提示资源未找到 |
| 409 | 业务冲突 | 返回冲突原因 |
| 500 | 服务器内部错误 | 记录日志，返回通用错误 |

### 业务异常处理

| 场景 | 异常类型 | 处理策略 |
|------|----------|----------|
| 库存不足 | StockInsufficientError | 返回可用库存数量，提示用户 |
| 订单已支付 | OrderAlreadyPaidError | 返回订单状态，禁止重复支付 |
| 促销已过期 | PromoExpiredError | 使用原价计算 |
| 会员不存在 | MemberNotFoundError | 提示注册会员 |
| 采购订单已入库 | PoAlreadyStockedInError | 禁止重复入库 |

### 分布式事务处理

采用最终一致性方案：
1. 本地事务 + 事件发布：业务操作和事件发布在同一本地事务中
2. 事件消费重试：消费失败自动重试，超过阈值进入死信队列
3. 补偿机制：提供手动补偿接口处理异常情况

## 测试策略

### 单元测试

- 使用 **pytest + pytest-asyncio** 进行单元测试
- 覆盖所有核心业务逻辑
- 测试边界条件和异常情况

### 属性测试

- 使用 **Hypothesis** 作为属性测试框架
- 每个属性测试运行至少 100 次迭代
- 测试标注格式：`**Feature: erp-retail-system, Property {number}: {property_text}**`

### 集成测试

- 使用 **testcontainers-python** 进行数据库集成测试
- 使用 Kafka 测试容器进行消息集成测试
- 验证服务间调用的正确性

### 端到端测试

- 模拟完整业务流程
- 验证 POS 开单、生产领料、采购入库三条核心链路

## 补充设计细节

### 服务详细设计

#### ① 商品中心 (item_service)

**职责边界：**
- 商品主档的唯一数据源
- SKU_ID 生成与管理
- 商品分类、条码、规格管理
- 商品状态生命周期管理

**SKU_ID 生成规则：**
```
格式: {类目前缀2位}{年月4位}{序列号6位}
示例: SP202401000001
生成策略: Redis INCR + 本地缓存号段
```

**商品状态机：**
```mermaid
stateDiagram-v2
    [*] --> 草稿: 创建
    草稿 --> 待审核: 提交
    待审核 --> 已上架: 审核通过
    待审核 --> 草稿: 审核驳回
    已上架 --> 已下架: 下架
    已下架 --> 已上架: 重新上架
    已下架 --> 已停用: 停用
```

**核心接口详细设计：**

```python
# schemas.py - Pydantic 数据模型

from pydantic import BaseModel
from typing import Optional, List

class SkuSpec(BaseModel):
    name: str
    value: str

class ItemCreateRequest(BaseModel):
    name: str                           # 商品名称
    category_id: Optional[int] = None   # 分类ID
    unit: Optional[str] = None          # 计量单位
    specs: List[SkuSpec] = []           # 规格列表
    barcodes: List[str] = []            # 条码列表

class ItemQueryRequest(BaseModel):
    keyword: Optional[str] = None       # 关键词
    category_id: Optional[int] = None   # 分类ID
    status: Optional[int] = None        # 状态
    page: int = 1                       # 页码
    size: int = 20                      # 每页数量
```

#### ② 用户中心 (user_service)

**认证流程：**
```mermaid
sequenceDiagram
    participant Client as 客户端
    participant Nginx as Nginx网关
    participant User as 用户中心
    participant Redis as Redis
    
    Client->>Nginx: 1. 登录请求(username, password)
    Nginx->>User: 2. 转发登录请求
    User->>User: 3. 验证密码(BCrypt)
    User->>Redis: 4. 存储Token
    User-->>Nginx: 5. 返回Token
    Nginx-->>Client: 6. 返回Token
    
    Client->>Nginx: 7. 业务请求(带Token)
    Nginx->>User: 8. /user/verify 验证Token
    User->>Redis: 9. 查询Token
    User-->>Nginx: 10. Token有效+用户信息
    Nginx->>Service: 11. 转发请求(带用户头)
```

**预置角色：**
| 角色代码 | 角色名称 | 权限范围 |
|----------|----------|----------|
| ADMIN | 系统管理员 | 全部权限 |
| STORE_MANAGER | 门店店长 | 门店管理、销售、库存查询 |
| CASHIER | 收银员 | POS收银、会员查询 |
| WAREHOUSE | 仓库管理员 | 库存管理、采购收货 |
| PURCHASER | 采购员 | 采购订单管理 |
| PRODUCTION | 生产计划员 | 生产订单、BOM管理 |
| WORKER | 生产工人 | 报工 |
| FINANCE | 财务人员 | 成本查询、报表 |

**JWT 认证实现：**

```python
# utils/jwt_utils.py

from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional, List

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class TokenData(BaseModel):
    user_id: int
    username: str
    roles: List[str] = []

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[TokenData]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(**payload)
    except JWTError:
        return None
```

#### ③ 采购中心 (purchase_service)

**采购订单状态机：**
```mermaid
stateDiagram-v2
    [*] --> 草稿: 创建
    草稿 --> 待审批: 提交
    待审批 --> 已审批: 审批通过
    待审批 --> 草稿: 审批驳回
    已审批 --> 部分入库: 部分收货
    已审批 --> 已入库: 全部收货
    部分入库 --> 已入库: 全部收货
    草稿 --> 已取消: 取消
    待审批 --> 已取消: 取消
```

**收货入库流程：**
```mermaid
sequenceDiagram
    participant WH as 仓库管理员
    participant PO as 采购中心
    participant STOCK as 库存中心
    participant COST as 成本中心
    participant KAFKA as Kafka
    
    WH->>PO: 1. 确认收货(po_id, items)
    PO->>PO: 2. 校验采购订单状态
    PO->>STOCK: 3. /stock/in 入库
    STOCK->>STOCK: 4. 更新库存
    STOCK->>KAFKA: 5. StockIn事件
    STOCK-->>PO: 6. 入库成功
    PO->>PO: 7. 更新收货数量
    PO->>KAFKA: 8. PoInStock事件
    KAFKA->>COST: 9. 消费事件
    COST->>COST: 10. 重算成本
```

#### ④ 生产中心 (production_service)

**BOM 结构设计：**
```sql
-- BOM 模板表（标准BOM）
CREATE TABLE bom_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_sku_id VARCHAR(32) NOT NULL COMMENT '成品SKU',
    version VARCHAR(20) NOT NULL COMMENT '版本号',
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sku_version (product_sku_id, version)
);

-- BOM 模板明细
CREATE TABLE bom_template_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    bom_id BIGINT NOT NULL,
    material_sku_id VARCHAR(32) NOT NULL COMMENT '原材料SKU',
    quantity DECIMAL(10,4) NOT NULL COMMENT '单位用量',
    loss_rate DECIMAL(5,2) DEFAULT 0 COMMENT '损耗率%',
    FOREIGN KEY (bom_id) REFERENCES bom_template(id)
);
```

**生产订单状态机：**
```mermaid
stateDiagram-v2
    [*] --> 草稿: 创建
    草稿 --> 已下达: 下达
    已下达 --> 生产中: 开始生产
    生产中 --> 已完工: 全部完工
    生产中 --> 已完工: 强制完工
    草稿 --> 已取消: 取消
    已下达 --> 已取消: 取消
```

#### ⑤ 报工中心 (job_service)

**报工流程：**
```mermaid
sequenceDiagram
    participant Worker as 工人
    participant APP as 报工APP
    participant JOB as 报工中心
    participant MO as 生产中心
    participant KAFKA as Kafka
    
    Worker->>APP: 1. 扫码报工
    APP->>JOB: 2. 提交报工(mo_id, routing_id, qty)
    JOB->>MO: 3. 查询生产订单
    MO-->>JOB: 4. 返回订单信息
    JOB->>JOB: 5. 校验报工数量
    alt 数量异常
        JOB->>JOB: 6a. 标记异常
    end
    JOB->>JOB: 6b. 保存报工记录
    JOB->>KAFKA: 7. JobReported事件
    JOB->>JOB: 8. 检查是否全部完工
    alt 全部完工
        JOB->>KAFKA: 9. MoCompleted事件
    end
    JOB-->>APP: 10. 报工成功
```

#### ⑥ 库存中心 (stock_service)

**库存操作类型：**
| 操作类型 | 代码 | 影响 | 触发场景 |
|----------|------|------|----------|
| 采购入库 | PO_IN | +库存 | 采购收货 |
| 生产入库 | MO_IN | +库存 | 生产完工 |
| 销售出库 | SO_OUT | -库存 | 订单发货 |
| 生产领料 | MO_OUT | -库存 | 生产开始 |
| 盘盈入库 | ADJ_IN | +库存 | 盘点盈余 |
| 盘亏出库 | ADJ_OUT | -库存 | 盘点亏损 |
| 调拨出库 | TF_OUT | -库存 | 仓库调拨 |
| 调拨入库 | TF_IN | +库存 | 仓库调拨 |

**库存锁定机制：**

```python
# schemas.py

from pydantic import BaseModel
from typing import List
from decimal import Decimal

class LockItem(BaseModel):
    sku_id: str
    warehouse_id: int
    quantity: Decimal

class StockLockRequest(BaseModel):
    order_id: str           # 订单ID
    order_type: str         # 订单类型: SO/MO
    items: List[LockItem]   # 锁定明细

# service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from erp_common.exceptions import StockInsufficientError

async def lock_stock(db: AsyncSession, request: StockLockRequest):
    """锁定库存"""
    async with db.begin():
        for item in request.items:
            # 1. 查询可用库存 (使用 FOR UPDATE 锁定行)
            result = await db.execute(
                select(Stock)
                .where(Stock.sku_id == item.sku_id)
                .where(Stock.warehouse_id == item.warehouse_id)
                .with_for_update()
            )
            stock = result.scalar_one_or_none()
            
            if not stock or stock.available_qty < item.quantity:
                raise StockInsufficientError(
                    sku_id=item.sku_id,
                    available=stock.available_qty if stock else 0,
                    required=item.quantity
                )
            
            # 2. 增加锁定数量
            await db.execute(
                update(Stock)
                .where(Stock.id == stock.id)
                .values(locked_qty=Stock.locked_qty + item.quantity)
            )
            
            # 3. 记录锁定明细
            lock_record = StockLock(
                order_id=request.order_id,
                order_type=request.order_type,
                sku_id=item.sku_id,
                warehouse_id=item.warehouse_id,
                quantity=item.quantity
            )
            db.add(lock_record)
```

#### ⑦ 成本中心 (cost_service)

**成本计算方法：**

1. **移动加权平均法（采购成本）：**
```
新单位成本 = (原库存金额 + 本次入库金额) / (原库存数量 + 本次入库数量)
```

2. **标准成本法（生产成本）：**
```
生产成本 = 直接材料成本 + 直接人工成本 + 制造费用
直接材料成本 = Σ(BOM用量 × 材料单位成本)
直接人工成本 = 实际工时 × 工时费率
```

**成本计算流程：**
```mermaid
sequenceDiagram
    participant KAFKA as Kafka
    participant COST as 成本中心
    participant STOCK as 库存中心
    participant DB as 数据库
    
    KAFKA->>COST: 1. StockIn事件
    COST->>STOCK: 2. 查询入库明细
    STOCK-->>COST: 3. 返回入库信息
    COST->>DB: 4. 查询当前成本
    COST->>COST: 5. 计算新成本
    COST->>DB: 6. 更新cost_sheet
    COST->>KAFKA: 7. CostCalculated事件
```

#### ⑧ 订单中心 (order_service)

**订单状态机：**
```mermaid
stateDiagram-v2
    [*] --> 待付款: 创建订单
    待付款 --> 已付款: 支付成功
    待付款 --> 已取消: 超时/取消
    已付款 --> 已发货: 发货
    已发货 --> 已完成: 确认收货
    已付款 --> 退款中: 申请退款
    退款中 --> 已退款: 退款成功
```

**订单号生成规则：**
```
格式: {渠道1位}{门店4位}{日期8位}{序列号6位}
示例: P0001202401150001
渠道: P=POS, M=小程序, W=Web
```

**订单创建流程：**
```mermaid
sequenceDiagram
    participant Client as 客户端
    participant ORDER as 订单中心
    participant PROMO as 促销中心
    participant STOCK as 库存中心
    participant MEMBER as 会员中心
    
    Client->>ORDER: 1. 创建订单请求
    ORDER->>PROMO: 2. /promo/calc 算价
    PROMO-->>ORDER: 3. 返回促销价格
    ORDER->>STOCK: 4. /stock/lock 锁库存
    alt 库存不足
        STOCK-->>ORDER: 5a. 库存不足
        ORDER-->>Client: 返回错误
    end
    STOCK-->>ORDER: 5b. 锁定成功
    ORDER->>ORDER: 6. 创建订单记录
    ORDER->>MEMBER: 7. 查询会员信息(可选)
    ORDER-->>Client: 8. 返回订单信息
```

#### ⑨ 会员中心 (member_service)

**会员等级规则：**
| 等级 | 名称 | 累计消费(元) | 积分倍率 | 折扣 |
|------|------|-------------|----------|------|
| 1 | 普通会员 | 0 | 1x | 无 |
| 2 | 银卡会员 | 1,000 | 1.2x | 98折 |
| 3 | 金卡会员 | 5,000 | 1.5x | 95折 |
| 4 | 钻石会员 | 20,000 | 2x | 90折 |

**积分规则：**
```
消费积分: 消费金额 × 积分倍率 (1元=1积分)
积分抵扣: 100积分 = 1元
积分有效期: 获取后12个月
```

**积分变动流程：**

```python
# service.py

from sqlalchemy.ext.asyncio import AsyncSession
from erp_common.exceptions import PointInsufficientError
from erp_common.utils.kafka_utils import KafkaProducer

async def change_points(
    db: AsyncSession, 
    kafka: KafkaProducer,
    request: PointChangeRequest
):
    """积分变动"""
    async with db.begin():
        # 1. 查询会员
        member = await db.get(Member, request.member_id)
        if not member:
            raise MemberNotFoundError(member_id=request.member_id)
        
        # 2. 计算新积分
        new_points = member.available_points + request.points
        if new_points < 0:
            raise PointInsufficientError(
                available=member.available_points,
                required=abs(request.points)
            )
        
        # 3. 更新会员积分
        member.available_points = new_points
        if request.points > 0:
            member.total_points += request.points
        
        # 4. 记录积分流水
        point_record = MemberPoint(
            member_id=request.member_id,
            change_type=request.change_type,
            points=request.points,
            ref_type=request.ref_type,
            ref_id=request.ref_id
        )
        db.add(point_record)
        
        # 5. 发布事件
        await kafka.send(
            topic="member-events",
            event=MemberPointChangedEvent(
                member_id=request.member_id,
                points=request.points,
                change_type=request.change_type
            )
        )
        
        # 6. 检查等级升级
        await check_and_upgrade_level(db, member)
```

#### ⑩ 促销中心 (promo_service)

**促销类型：**
| 类型 | 代码 | 描述 | 示例 |
|------|------|------|------|
| 满减 | FULL_MINUS | 满X元减Y元 | 满100减20 |
| 折扣 | DISCOUNT | 打X折 | 8折 |
| 买赠 | BUY_GIFT | 买X送Y | 买2送1 |
| 特价 | SPECIAL | 固定价格 | 特价9.9 |
| 组合 | BUNDLE | 组合优惠 | A+B=50元 |

**促销规则配置：**
```json
// 满减规则示例
{
  "type": "FULL_MINUS",
  "condition": {
    "minAmount": 100,
    "skuIds": ["SKU001", "SKU002"],
    "categoryIds": [1, 2]
  },
  "action": {
    "discountAmount": 20
  }
}

// 折扣规则示例
{
  "type": "DISCOUNT",
  "condition": {
    "skuIds": ["SKU003"]
  },
  "action": {
    "discountRate": 0.8
  }
}
```

**算价逻辑：**

```python
# service.py

from datetime import datetime
from typing import List
from decimal import Decimal

async def calculate(db: AsyncSession, request: CalcRequest) -> CalcResult:
    """计算促销价格"""
    # 1. 查询适用的促销活动
    now = datetime.now()
    promos = await db.execute(
        select(Promo)
        .where(Promo.status == 1)
        .where(Promo.start_time <= now)
        .where(Promo.end_time >= now)
    )
    promos = promos.scalars().all()
    
    # 2. 按优先级排序
    promos = sorted(promos, key=lambda p: p.priority, reverse=True)
    
    # 3. 计算每个促销的优惠金额
    results: List[PromoResult] = []
    for promo in promos:
        result = await calculate_promo(promo, request)
        if result.discount_amount > Decimal("0"):
            results.append(result)
    
    # 4. 选择最优惠的促销
    return select_best_promo(results)

def select_best_promo(results: List[PromoResult]) -> CalcResult:
    """选择最优惠的促销方案"""
    if not results:
        return CalcResult(discount_amount=Decimal("0"))
    
    # 按优惠金额降序排序，选择最大的
    best = max(results, key=lambda r: r.discount_amount)
    return CalcResult(
        promo_id=best.promo_id,
        promo_name=best.promo_name,
        discount_amount=best.discount_amount
    )
```

### POS 离线架构

**本地数据库结构：**
```sql
-- SQLite 离线订单表
CREATE TABLE offline_order (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    order_data TEXT NOT NULL,  -- JSON格式订单数据
    status INTEGER DEFAULT 0,  -- 0待同步 1已同步 -1同步失败
    created_at TEXT NOT NULL,
    synced_at TEXT,
    error_msg TEXT
);

-- SQLite 商品缓存表
CREATE TABLE item_cache (
    sku_id TEXT PRIMARY KEY,
    item_data TEXT NOT NULL,  -- JSON格式商品数据
    updated_at TEXT NOT NULL
);

-- SQLite 库存缓存表
CREATE TABLE stock_cache (
    sku_id TEXT PRIMARY KEY,
    quantity REAL NOT NULL,
    updated_at TEXT NOT NULL
);
```

**离线同步流程：**
```mermaid
sequenceDiagram
    participant POS as POS终端
    participant SQLite as 本地SQLite
    participant GW as Nginx网关
    participant ORDER as 订单中心
    
    Note over POS: 网络恢复
    POS->>SQLite: 1. 查询待同步订单
    SQLite-->>POS: 2. 返回订单列表(按时间排序)
    loop 逐笔同步
        POS->>GW: 3. /order/sync
        GW->>ORDER: 4. 创建订单
        alt 同步成功
            ORDER-->>POS: 5a. 返回成功
            POS->>SQLite: 6a. 更新状态=已同步
        else 同步失败
            ORDER-->>POS: 5b. 返回错误
            POS->>SQLite: 6b. 更新状态=失败,记录错误
        end
    end
```

### 网关层设计 (Nginx)

**Nginx 配置：**

```nginx
# nginx.conf

# 限流配置
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req_zone $binary_remote_addr zone=stock_limit:10m rate=500r/s;

# 上游服务定义
upstream item_service {
    server item-service-1:8001;
    server item-service-2:8001;
    keepalive 32;
}

upstream user_service {
    server user-service-1:8002;
    server user-service-2:8002;
    keepalive 32;
}

upstream stock_service {
    server stock-service-1:8003;
    server stock-service-2:8003;
    server stock-service-3:8003;
    keepalive 64;
}

upstream order_service {
    server order-service-1:8004;
    server order-service-2:8004;
    keepalive 32;
}

upstream promo_service {
    server promo-service-1:8005;
    keepalive 16;
}

upstream member_service {
    server member-service-1:8006;
    keepalive 16;
}

server {
    listen 80;
    server_name api.erp.local;

    # CORS 配置
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS';
    add_header Access-Control-Allow-Headers 'Authorization, Content-Type';

    # 白名单路由 (无需认证)
    location /user/login {
        proxy_pass http://user_service;
    }
    
    location /user/register {
        proxy_pass http://user_service;
    }

    # 需要认证的路由
    location /item/ {
        limit_req zone=api_limit burst=20 nodelay;
        auth_request /auth/verify;
        auth_request_set $user_id $upstream_http_x_user_id;
        auth_request_set $user_roles $upstream_http_x_user_roles;
        proxy_set_header X-User-Id $user_id;
        proxy_set_header X-User-Roles $user_roles;
        proxy_pass http://item_service;
    }

    location /stock/ {
        limit_req zone=stock_limit burst=50 nodelay;
        auth_request /auth/verify;
        auth_request_set $user_id $upstream_http_x_user_id;
        proxy_set_header X-User-Id $user_id;
        proxy_pass http://stock_service;
    }

    location /order/ {
        limit_req zone=api_limit burst=20 nodelay;
        auth_request /auth/verify;
        auth_request_set $user_id $upstream_http_x_user_id;
        proxy_set_header X-User-Id $user_id;
        proxy_pass http://order_service;
    }

    location /promo/ {
        limit_req zone=api_limit burst=20 nodelay;
        auth_request /auth/verify;
        proxy_pass http://promo_service;
    }

    location /member/ {
        limit_req zone=api_limit burst=20 nodelay;
        auth_request /auth/verify;
        proxy_pass http://member_service;
    }

    # 认证验证端点
    location = /auth/verify {
        internal;
        proxy_pass http://user_service/user/verify;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URI $request_uri;
    }
}
```

**FastAPI 认证依赖：**

```python
# erp_common/auth.py

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List

security = HTTPBearer(auto_error=False)

class CurrentUser:
    def __init__(self, user_id: int, roles: List[str]):
        self.user_id = user_id
        self.roles = roles

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """从请求头获取当前用户信息 (由 Nginx 注入)"""
    user_id = request.headers.get("X-User-Id")
    user_roles = request.headers.get("X-User-Roles", "")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return CurrentUser(
        user_id=int(user_id),
        roles=user_roles.split(",") if user_roles else []
    )

def require_roles(*required_roles: str):
    """角色权限校验装饰器"""
    async def role_checker(user: CurrentUser = Depends(get_current_user)):
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return user
    return role_checker
```

### 事件消息格式

**统一事件结构：**

```python
# erp_common/schemas/events.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional
import uuid

class DomainEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    operator: Optional[str] = None
    payload: Any = None
```

**事件示例：**
```json
{
  "event_id": "evt_20240115_001",
  "event_type": "OrderPaid",
  "aggregate_id": "P0001202401150001",
  "aggregate_type": "SalesOrder",
  "occurred_at": "2024-01-15T10:30:00",
  "operator": "user_001",
  "payload": {
    "orderId": "P0001202401150001",
    "payAmount": 99.00,
    "payMethod": "WECHAT",
    "items": [
      {"skuId": "SKU001", "quantity": 2, "price": 49.50}
    ]
  }
}
```

**Kafka 工具类：**

```python
# erp_common/utils/kafka_utils.py

import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from typing import Callable, Awaitable
from erp_common.schemas.events import DomainEvent

class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None
    
    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode()
        )
        await self._producer.start()
    
    async def stop(self):
        if self._producer:
            await self._producer.stop()
    
    async def send(self, topic: str, event: DomainEvent):
        await self._producer.send_and_wait(
            topic, 
            value=event.model_dump()
        )

class KafkaConsumer:
    def __init__(
        self, 
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        handler: Callable[[dict], Awaitable[None]]
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.handler = handler
        self._consumer = None
        self._running = False
    
    async def start(self):
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda v: json.loads(v.decode())
        )
        await self._consumer.start()
        self._running = True
        
        async for msg in self._consumer:
            if not self._running:
                break
            try:
                await self.handler(msg.value)
            except Exception as e:
                # 记录错误，发送到死信队列
                print(f"Error processing message: {e}")
    
    async def stop(self):
        self._running = False
        if self._consumer:
            await self._consumer.stop()
```

### 部署架构

```mermaid
graph TB
    subgraph 负载均衡
        LB[Nginx/SLB]
    end
    
    subgraph 网关层
        NGINX1[Nginx-1]
        NGINX2[Nginx-2]
    end
    
    subgraph 服务集群
        subgraph 商品服务
            ITEM1[item-service-1]
            ITEM2[item-service-2]
        end
        subgraph 库存服务
            STOCK1[stock-service-1]
            STOCK2[stock-service-2]
            STOCK3[stock-service-3]
        end
        subgraph 订单服务
            ORDER1[order-service-1]
            ORDER2[order-service-2]
        end
    end
    
    subgraph 中间件
        CONSUL[Consul集群]
        KAFKA[Kafka集群]
        REDIS[Redis集群]
    end
    
    subgraph 数据库
        MYSQL_M[(MySQL主库)]
        MYSQL_S[(MySQL从库)]
        STOCK_DB[(库存分库×4)]
    end
    
    LB --> NGINX1
    LB --> NGINX2
    NGINX1 --> ITEM1
    NGINX1 --> STOCK1
    NGINX1 --> ORDER1
    NGINX2 --> ITEM2
    NGINX2 --> STOCK2
    NGINX2 --> ORDER2
    
    ITEM1 --> CONSUL
    STOCK1 --> CONSUL
    ORDER1 --> CONSUL
    
    ITEM1 --> KAFKA
    STOCK1 --> KAFKA
    ORDER1 --> KAFKA
    
    ITEM1 --> REDIS
    STOCK1 --> REDIS
    ORDER1 --> REDIS
    
    ITEM1 --> MYSQL_M
    ORDER1 --> MYSQL_M
    STOCK1 --> STOCK_DB
    
    MYSQL_M --> MYSQL_S
```

### Docker 部署配置

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  # Nginx 网关
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - item-service
      - user-service
      - stock-service
      - order-service

  # 商品服务
  item-service:
    build:
      context: .
      dockerfile: services/item_service/Dockerfile
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@mysql:3306/erp
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - mysql
      - redis
      - kafka

  # 用户服务
  user-service:
    build:
      context: .
      dockerfile: services/user_service/Dockerfile
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@mysql:3306/erp
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=your-secret-key

  # 库存服务
  stock-service:
    build:
      context: .
      dockerfile: services/stock_service/Dockerfile
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@mysql:3306/erp_stock
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092

  # 订单服务
  order-service:
    build:
      context: .
      dockerfile: services/order_service/Dockerfile
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@mysql:3306/erp
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092

  # MySQL
  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql

  # Redis
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # Kafka
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
    depends_on:
      - zookeeper

  # Zookeeper
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      - ZOOKEEPER_CLIENT_PORT=2181

volumes:
  mysql_data:
  redis_data:
```

**Dockerfile 示例：**

```dockerfile
# services/item_service/Dockerfile

FROM python:3.11-slim as builder

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl && rm *.whl

COPY erp_common/ ./erp_common/
COPY services/item_service/ ./services/item_service/

EXPOSE 8001
CMD ["uvicorn", "services.item_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 监控与告警

**监控指标：**
| 指标类型 | 指标名称 | 告警阈值 |
|----------|----------|----------|
| 服务健康 | 服务存活状态 | 服务下线 |
| 响应时间 | API P99延迟 | > 500ms |
| 错误率 | 5xx错误率 | > 1% |
| 库存 | 库存预警 | < 安全库存 |
| 消息 | 消息积压数 | > 10000 |
| 数据库 | 连接池使用率 | > 80% |

**日志规范（结构化日志）：**

```python
# erp_common/logging.py

import logging
import json
from datetime import datetime
from typing import Any

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
            "user_id": getattr(record, "user_id", None),
            "message": record.getMessage(),
            "data": getattr(record, "data", None)
        }
        return json.dumps(log_data, default=str)

def setup_logging(service_name: str):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger(service_name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger
```

**日志输出示例：**
```json
{
  "timestamp": "2024-01-15T10:30:00.123",
  "level": "INFO",
  "service": "order-service",
  "trace_id": "trace_001",
  "span_id": "span_001",
  "user_id": "user_001",
  "message": "订单创建成功",
  "data": {
    "orderId": "P0001202401150001",
    "amount": 99.00
  }
}
```