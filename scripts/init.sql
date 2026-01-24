-- ERP System 数据库初始化脚本
-- 适用于 MySQL 8.0+

-- 创建数据库
CREATE DATABASE IF NOT EXISTS erp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE erp;

-- ==================== 商品中心表 ====================

-- 商品分类表
CREATE TABLE IF NOT EXISTS item_category (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '分类名称',
    parent_id BIGINT DEFAULT 0 COMMENT '父分类ID',
    level INT DEFAULT 1 COMMENT '层级',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- 商品主表
CREATE TABLE IF NOT EXISTS item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) UNIQUE NOT NULL COMMENT '全局唯一SKU编码',
    name VARCHAR(200) NOT NULL COMMENT '商品名称',
    category_id BIGINT COMMENT '分类ID',
    unit VARCHAR(20) COMMENT '计量单位',
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0停用',
    description TEXT COMMENT '商品描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category_id),
    INDEX idx_status (status),
    FULLTEXT INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品主表';

-- 商品SKU表
CREATE TABLE IF NOT EXISTS item_sku (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    item_id BIGINT NOT NULL,
    sku_id VARCHAR(32) UNIQUE NOT NULL,
    spec_info JSON COMMENT '规格信息',
    price DECIMAL(10,2) COMMENT '销售价',
    cost DECIMAL(10,2) COMMENT '成本价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_item (item_id),
    FOREIGN KEY (item_id) REFERENCES item(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品SKU表';

-- 商品条码表
CREATE TABLE IF NOT EXISTS item_barcode (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    item_id BIGINT NOT NULL,
    sku_id VARCHAR(32) NOT NULL,
    barcode VARCHAR(50) NOT NULL,
    is_primary TINYINT DEFAULT 0 COMMENT '是否主条码',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_barcode (barcode),
    INDEX idx_item (item_id),
    INDEX idx_sku (sku_id),
    FOREIGN KEY (item_id) REFERENCES item(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品条码表';

-- ==================== 用户中心表 ====================

-- 组织表
CREATE TABLE IF NOT EXISTS org (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(32) UNIQUE NOT NULL COMMENT '组织编码',
    name VARCHAR(200) NOT NULL COMMENT '组织名称',
    type VARCHAR(20) NOT NULL COMMENT '类型: STORE/WAREHOUSE/SUPPLIER/DEPT',
    parent_id BIGINT DEFAULT 0 COMMENT '父组织ID',
    status TINYINT DEFAULT 1 COMMENT '状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组织表';

-- 用户表
CREATE TABLE IF NOT EXISTS user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    password VARCHAR(100) NOT NULL COMMENT '密码哈希',
    name VARCHAR(50) COMMENT '姓名',
    mobile VARCHAR(20) COMMENT '手机号',
    email VARCHAR(100) COMMENT '邮箱',
    org_id BIGINT COMMENT '所属组织',
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0停用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_org (org_id),
    INDEX idx_mobile (mobile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 角色表
CREATE TABLE IF NOT EXISTS role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '角色编码',
    name VARCHAR(100) NOT NULL COMMENT '角色名称',
    description VARCHAR(500) COMMENT '描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 权限表
CREATE TABLE IF NOT EXISTS permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(100) UNIQUE NOT NULL COMMENT '权限编码',
    name VARCHAR(100) NOT NULL COMMENT '权限名称',
    resource VARCHAR(200) COMMENT '资源路径',
    action VARCHAR(20) COMMENT '操作: READ/WRITE/DELETE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS user_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    role_code VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_role (user_id, role_code),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS role_permission (
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permission(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';

-- ==================== 库存中心表 ====================

-- 仓库表
CREATE TABLE IF NOT EXISTS warehouse (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(32) UNIQUE NOT NULL COMMENT '仓库编码',
    name VARCHAR(200) NOT NULL COMMENT '仓库名称',
    type VARCHAR(20) COMMENT '类型: MAIN/BRANCH/VIRTUAL',
    address VARCHAR(500) COMMENT '地址',
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库表';

-- 库存主表
CREATE TABLE IF NOT EXISTS stock (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    warehouse_id BIGINT NOT NULL COMMENT '仓库ID',
    quantity DECIMAL(10,2) DEFAULT 0 COMMENT '实际库存',
    locked_qty DECIMAL(10,2) DEFAULT 0 COMMENT '锁定数量',
    available_qty DECIMAL(10,2) GENERATED ALWAYS AS (quantity - locked_qty) STORED COMMENT '可用库存',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sku_wh (sku_id, warehouse_id),
    INDEX idx_warehouse (warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存主表';

-- 库存明细表
CREATE TABLE IF NOT EXISTS stock_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    warehouse_id BIGINT NOT NULL,
    batch_no VARCHAR(50) COMMENT '批次号',
    quantity DECIMAL(10,2) DEFAULT 0,
    locked_qty DECIMAL(10,2) DEFAULT 0,
    cost DECIMAL(10,2) COMMENT '批次成本',
    expire_date DATE COMMENT '过期日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sku_wh (sku_id, warehouse_id),
    INDEX idx_batch (batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存明细表';

-- 库存流水表
CREATE TABLE IF NOT EXISTS stock_move (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    warehouse_id BIGINT NOT NULL,
    move_type VARCHAR(20) NOT NULL COMMENT '类型: IN/OUT/LOCK/UNLOCK',
    quantity DECIMAL(10,2) NOT NULL,
    ref_type VARCHAR(20) COMMENT '关联单据类型: PO/MO/SO',
    ref_id BIGINT COMMENT '关联单据ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sku (sku_id),
    INDEX idx_ref (ref_type, ref_id),
    INDEX idx_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存流水表';

-- 库存锁定记录表
CREATE TABLE IF NOT EXISTS stock_lock (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(50) NOT NULL COMMENT '订单ID',
    order_type VARCHAR(20) NOT NULL COMMENT '订单类型: SO/MO',
    sku_id VARCHAR(32) NOT NULL,
    warehouse_id BIGINT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL COMMENT '锁定数量',
    status TINYINT DEFAULT 1 COMMENT '状态: 1有效 0已释放',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order (order_id, order_type),
    INDEX idx_sku (sku_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存锁定记录表';

-- ==================== 订单中心表 ====================

-- 销售订单主表
CREATE TABLE IF NOT EXISTS so_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(32) UNIQUE NOT NULL COMMENT '订单号',
    member_id BIGINT COMMENT '会员ID',
    store_id BIGINT COMMENT '门店ID',
    warehouse_id BIGINT COMMENT '发货仓库',
    total_amount DECIMAL(10,2) NOT NULL COMMENT '订单总额',
    discount_amount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠金额',
    pay_amount DECIMAL(10,2) NOT NULL COMMENT '实付金额',
    status TINYINT DEFAULT 0 COMMENT '状态: 0待付款 1已付款 2已发货 3已完成 -1已取消',
    source VARCHAR(20) COMMENT '来源: POS/MP/WEB',
    remark VARCHAR(500) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_member (member_id),
    INDEX idx_store (store_id),
    INDEX idx_status (status),
    INDEX idx_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售订单主表';

-- 销售订单明细表
CREATE TABLE IF NOT EXISTS so_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    sku_id VARCHAR(32) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    price DECIMAL(10,2) NOT NULL COMMENT '单价',
    discount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠',
    amount DECIMAL(10,2) NOT NULL COMMENT '小计',
    INDEX idx_order (order_id),
    INDEX idx_sku (sku_id),
    FOREIGN KEY (order_id) REFERENCES so_order(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售订单明细表';

-- 支付记录表
CREATE TABLE IF NOT EXISTS payment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    pay_method VARCHAR(20) NOT NULL COMMENT '支付方式: CASH/WECHAT/ALIPAY/CARD',
    amount DECIMAL(10,2) NOT NULL,
    status TINYINT DEFAULT 0 COMMENT '状态: 0待支付 1成功 -1失败',
    pay_time DATETIME COMMENT '支付时间',
    trade_no VARCHAR(64) COMMENT '第三方交易号',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order (order_id),
    INDEX idx_status (status),
    FOREIGN KEY (order_id) REFERENCES so_order(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付记录表';

-- ==================== 会员中心表 ====================

-- 会员表
CREATE TABLE IF NOT EXISTS member (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mobile VARCHAR(20) UNIQUE NOT NULL COMMENT '手机号',
    name VARCHAR(50) COMMENT '姓名',
    level INT DEFAULT 1 COMMENT '会员等级',
    total_points INT DEFAULT 0 COMMENT '累计积分',
    available_points INT DEFAULT 0 COMMENT '可用积分',
    total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '累计消费',
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员表';

-- 会员积分表
CREATE TABLE IF NOT EXISTS member_point (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    change_type VARCHAR(20) NOT NULL COMMENT '类型: EARN/USE/EXPIRE/ADJUST',
    points INT NOT NULL COMMENT '变动积分(正负)',
    balance INT NOT NULL COMMENT '变动后余额',
    ref_type VARCHAR(20) COMMENT '关联类型: ORDER/ACTIVITY',
    ref_id BIGINT COMMENT '关联ID',
    remark VARCHAR(200) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_member (member_id),
    INDEX idx_time (created_at),
    FOREIGN KEY (member_id) REFERENCES member(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员积分表';

-- 会员优惠券表
CREATE TABLE IF NOT EXISTS member_coupon (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    coupon_id BIGINT NOT NULL,
    coupon_code VARCHAR(32) UNIQUE NOT NULL COMMENT '券码',
    status TINYINT DEFAULT 0 COMMENT '状态: 0未使用 1已使用 -1已过期',
    use_time DATETIME COMMENT '使用时间',
    use_order_id BIGINT COMMENT '使用订单ID',
    expire_time DATETIME NOT NULL COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_member (member_id),
    INDEX idx_status (status),
    FOREIGN KEY (member_id) REFERENCES member(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员优惠券表';

-- ==================== 促销中心表 ====================

-- 促销活动表
CREATE TABLE IF NOT EXISTS promo (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '活动名称',
    type VARCHAR(20) NOT NULL COMMENT '类型: FULL_MINUS/DISCOUNT/BUY_GIFT/SPECIAL/BUNDLE',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME NOT NULL COMMENT '结束时间',
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0停用',
    priority INT DEFAULT 0 COMMENT '优先级',
    description TEXT COMMENT '活动描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_time (start_time, end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='促销活动表';

-- 促销规则表
CREATE TABLE IF NOT EXISTS promo_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    promo_id BIGINT NOT NULL,
    rule_type VARCHAR(20) NOT NULL COMMENT '规则类型',
    condition_json JSON COMMENT '条件配置',
    action_json JSON COMMENT '动作配置',
    INDEX idx_promo (promo_id),
    FOREIGN KEY (promo_id) REFERENCES promo(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='促销规则表';

-- 促销记录表
CREATE TABLE IF NOT EXISTS promo_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    promo_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL COMMENT '优惠金额',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_promo (promo_id),
    INDEX idx_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='促销记录表';

-- ==================== 采购中心表 ====================

-- 供应商表
CREATE TABLE IF NOT EXISTS supplier (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(32) UNIQUE NOT NULL COMMENT '供应商编码',
    name VARCHAR(200) NOT NULL COMMENT '供应商名称',
    contact VARCHAR(50) COMMENT '联系人',
    phone VARCHAR(20) COMMENT '电话',
    address VARCHAR(500) COMMENT '地址',
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商表';

-- 采购订单主表
CREATE TABLE IF NOT EXISTS po_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    po_no VARCHAR(32) UNIQUE NOT NULL COMMENT '采购单号',
    supplier_id BIGINT NOT NULL COMMENT '供应商ID',
    warehouse_id BIGINT NOT NULL COMMENT '入库仓库',
    total_amount DECIMAL(12,2) NOT NULL COMMENT '采购金额',
    status TINYINT DEFAULT 0 COMMENT '状态: 0草稿 1待审批 2已审批 3部分入库 4已入库 -1已取消',
    created_by BIGINT NOT NULL COMMENT '创建人',
    approved_by BIGINT COMMENT '审批人',
    approved_at DATETIME COMMENT '审批时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_supplier (supplier_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采购订单主表';

-- 采购订单明细表
CREATE TABLE IF NOT EXISTS po_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    po_id BIGINT NOT NULL,
    sku_id VARCHAR(32) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL COMMENT '采购数量',
    price DECIMAL(10,2) NOT NULL COMMENT '采购单价',
    received_qty DECIMAL(10,2) DEFAULT 0 COMMENT '已入库数量',
    INDEX idx_po (po_id),
    FOREIGN KEY (po_id) REFERENCES po_order(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采购订单明细表';

-- ==================== 生产中心表 ====================

-- BOM 模板表
CREATE TABLE IF NOT EXISTS bom_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_sku_id VARCHAR(32) NOT NULL COMMENT '成品SKU',
    version VARCHAR(20) NOT NULL COMMENT '版本号',
    status TINYINT DEFAULT 1 COMMENT '状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sku_version (product_sku_id, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BOM模板表';

-- BOM 模板明细
CREATE TABLE IF NOT EXISTS bom_template_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    bom_id BIGINT NOT NULL,
    material_sku_id VARCHAR(32) NOT NULL COMMENT '原材料SKU',
    quantity DECIMAL(10,4) NOT NULL COMMENT '单位用量',
    loss_rate DECIMAL(5,2) DEFAULT 0 COMMENT '损耗率%',
    INDEX idx_bom (bom_id),
    FOREIGN KEY (bom_id) REFERENCES bom_template(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BOM模板明细表';

-- 生产订单主表
CREATE TABLE IF NOT EXISTS mo_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_no VARCHAR(32) UNIQUE NOT NULL COMMENT '生产单号',
    sku_id VARCHAR(32) NOT NULL COMMENT '成品SKU',
    plan_qty DECIMAL(10,2) NOT NULL COMMENT '计划数量',
    completed_qty DECIMAL(10,2) DEFAULT 0 COMMENT '完工数量',
    warehouse_id BIGINT NOT NULL COMMENT '入库仓库',
    status TINYINT DEFAULT 0 COMMENT '状态: 0草稿 1已下达 2生产中 3已完工 -1已取消',
    plan_start DATE COMMENT '计划开始',
    plan_end DATE COMMENT '计划结束',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sku (sku_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产订单主表';

-- MO BOM 物料清单表
CREATE TABLE IF NOT EXISTS mo_bom (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL,
    material_sku_id VARCHAR(32) NOT NULL COMMENT '原材料SKU',
    quantity DECIMAL(10,4) NOT NULL COMMENT '单位用量',
    issued_qty DECIMAL(10,2) DEFAULT 0 COMMENT '已领料数量',
    INDEX idx_mo (mo_id),
    FOREIGN KEY (mo_id) REFERENCES mo_order(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MO BOM物料清单表';

-- 工艺路线表
CREATE TABLE IF NOT EXISTS mo_routing (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL,
    seq INT NOT NULL COMMENT '工序顺序',
    operation_name VARCHAR(100) NOT NULL COMMENT '工序名称',
    work_center VARCHAR(50) COMMENT '工作中心',
    std_hours DECIMAL(6,2) COMMENT '标准工时',
    INDEX idx_mo (mo_id),
    FOREIGN KEY (mo_id) REFERENCES mo_order(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工艺路线表';

-- ==================== 报工中心表 ====================

-- 报工记录表
CREATE TABLE IF NOT EXISTS report_job (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL COMMENT '生产订单ID',
    routing_id BIGINT NOT NULL COMMENT '工序ID',
    worker_id BIGINT NOT NULL COMMENT '工人ID',
    quantity DECIMAL(10,2) NOT NULL COMMENT '报工数量',
    work_hours DECIMAL(6,2) COMMENT '实际工时',
    report_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '报工时间',
    status TINYINT DEFAULT 1 COMMENT '状态: 1正常 0异常',
    INDEX idx_mo (mo_id),
    INDEX idx_worker (worker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报工记录表';

-- 损耗记录表
CREATE TABLE IF NOT EXISTS report_loss (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mo_id BIGINT NOT NULL,
    sku_id VARCHAR(32) NOT NULL COMMENT '损耗物料SKU',
    quantity DECIMAL(10,2) NOT NULL COMMENT '损耗数量',
    reason VARCHAR(200) COMMENT '损耗原因',
    report_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mo (mo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='损耗记录表';

-- ==================== 成本中心表 ====================

-- 成本表
CREATE TABLE IF NOT EXISTS cost_sheet (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id VARCHAR(32) NOT NULL,
    period VARCHAR(7) NOT NULL COMMENT '期间: YYYY-MM',
    cost_type VARCHAR(20) NOT NULL COMMENT '类型: PURCHASE/PRODUCE',
    unit_cost DECIMAL(12,4) NOT NULL COMMENT '单位成本',
    total_qty DECIMAL(12,2) NOT NULL COMMENT '总数量',
    total_amount DECIMAL(14,2) NOT NULL COMMENT '总金额',
    calc_method VARCHAR(20) COMMENT '计算方法: WEIGHTED_AVG/MOVING_AVG',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sku_period (sku_id, period, cost_type),
    INDEX idx_period (period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成本表';

-- 成本明细表
CREATE TABLE IF NOT EXISTS cost_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    cost_sheet_id BIGINT NOT NULL,
    ref_type VARCHAR(20) NOT NULL COMMENT '来源类型: PO/MO',
    ref_id BIGINT NOT NULL COMMENT '来源单据ID',
    quantity DECIMAL(10,2) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sheet (cost_sheet_id),
    FOREIGN KEY (cost_sheet_id) REFERENCES cost_sheet(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成本明细表';

-- ==================== 初始化数据 ====================

-- 插入默认角色
INSERT INTO role (code, name, description) VALUES
('ADMIN', '系统管理员', '拥有全部权限'),
('STORE_MANAGER', '门店店长', '门店管理、销售、库存查询'),
('CASHIER', '收银员', 'POS收银、会员查询'),
('WAREHOUSE', '仓库管理员', '库存管理、采购收货'),
('PURCHASER', '采购员', '采购订单管理'),
('PRODUCTION', '生产计划员', '生产订单、BOM管理'),
('WORKER', '生产工人', '报工'),
('FINANCE', '财务人员', '成本查询、报表')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 插入默认管理员用户 (密码: admin123)
INSERT INTO user (username, password, name, status) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.I5IAA.1J7KHKCi', '系统管理员', 1)
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 关联管理员角色
INSERT INTO user_role (user_id, role_code)
SELECT u.id, 'ADMIN' FROM user u WHERE u.username = 'admin'
ON DUPLICATE KEY UPDATE role_code=VALUES(role_code);

-- 插入默认仓库
INSERT INTO warehouse (code, name, type, status) VALUES
('WH001', '主仓库', 'MAIN', 1),
('WH002', '门店仓库', 'BRANCH', 1)
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 插入默认商品分类
INSERT INTO item_category (name, parent_id, level, sort_order) VALUES
('食品', 0, 1, 1),
('饮料', 0, 1, 2),
('日用品', 0, 1, 3),
('生鲜', 0, 1, 4)
ON DUPLICATE KEY UPDATE name=VALUES(name);

COMMIT;
