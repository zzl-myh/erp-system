-- 权限点初始化数据
-- 执行方式: docker exec -i erp-mysql-1 mysql -uroot -pX7kL9mP2qR5tlyzm erp < scripts/init_permissions.sql

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 清空现有数据
TRUNCATE TABLE role_permission;
TRUNCATE TABLE permission;

-- 插入权限点
INSERT INTO permission (id, code, name, resource, action, created_at) VALUES
-- 用户管理
(1, 'user:view', '查看用户', '/user', 'READ', NOW()),
(2, 'user:create', '创建用户', '/user', 'WRITE', NOW()),
(3, 'user:update', '更新用户', '/user', 'WRITE', NOW()),
(4, 'user:delete', '删除用户', '/user', 'DELETE', NOW()),
(5, 'user:reset_password', '重置密码', '/user', 'WRITE', NOW()),

-- 角色管理
(10, 'role:view', '查看角色', '/role', 'READ', NOW()),
(11, 'role:create', '创建角色', '/role', 'WRITE', NOW()),
(12, 'role:update', '更新角色', '/role', 'WRITE', NOW()),
(13, 'role:delete', '删除角色', '/role', 'DELETE', NOW()),
(14, 'role:assign', '分配用户角色', '/role', 'WRITE', NOW()),
(15, 'role:permission', '分配角色权限', '/role', 'WRITE', NOW()),

-- 组织管理
(20, 'org:view', '查看组织', '/org', 'READ', NOW()),
(21, 'org:create', '创建组织', '/org', 'WRITE', NOW()),
(22, 'org:update', '更新组织', '/org', 'WRITE', NOW()),
(23, 'org:delete', '删除组织', '/org', 'DELETE', NOW()),

-- 商品管理
(30, 'item:view', '查看商品', '/item', 'READ', NOW()),
(31, 'item:create', '创建商品', '/item', 'WRITE', NOW()),
(32, 'item:update', '更新商品', '/item', 'WRITE', NOW()),
(33, 'item:delete', '删除商品', '/item', 'DELETE', NOW()),

-- 库存管理
(40, 'stock:view', '查看库存', '/stock', 'READ', NOW()),
(41, 'stock:adjust', '库存调整', '/stock', 'WRITE', NOW()),
(42, 'stock:transfer', '库存调拨', '/stock', 'WRITE', NOW()),

-- 订单管理
(50, 'order:view', '查看订单', '/order', 'READ', NOW()),
(51, 'order:create', '创建订单', '/order', 'WRITE', NOW()),
(52, 'order:update', '更新订单', '/order', 'WRITE', NOW()),
(53, 'order:cancel', '取消订单', '/order', 'DELETE', NOW()),

-- 会员管理
(60, 'member:view', '查看会员', '/member', 'READ', NOW()),
(61, 'member:create', '创建会员', '/member', 'WRITE', NOW()),
(62, 'member:update', '更新会员', '/member', 'WRITE', NOW()),
(63, 'member:points', '积分操作', '/member', 'WRITE', NOW()),

-- 采购管理
(70, 'purchase:view', '查看采购单', '/po', 'READ', NOW()),
(71, 'purchase:create', '创建采购单', '/po', 'WRITE', NOW()),
(72, 'purchase:approve', '审批采购单', '/po', 'WRITE', NOW()),
(73, 'purchase:receive', '采购收货', '/po', 'WRITE', NOW()),

-- 生产管理
(80, 'production:view', '查看生产单', '/mo', 'READ', NOW()),
(81, 'production:create', '创建生产单', '/mo', 'WRITE', NOW()),
(82, 'production:update', '更新生产单', '/mo', 'WRITE', NOW()),
(83, 'production:complete', '完成生产单', '/mo', 'WRITE', NOW()),

-- 报工管理
(90, 'job:view', '查看报工', '/job', 'READ', NOW()),
(91, 'job:report', '提交报工', '/job', 'WRITE', NOW()),
(92, 'job:approve', '审批报工', '/job', 'WRITE', NOW()),

-- 成本管理
(100, 'cost:view', '查看成本', '/cost', 'READ', NOW()),
(101, 'cost:calculate', '成本核算', '/cost', 'WRITE', NOW()),

-- 促销管理
(110, 'promo:view', '查看促销', '/promo', 'READ', NOW()),
(111, 'promo:create', '创建促销', '/promo', 'WRITE', NOW()),
(112, 'promo:update', '更新促销', '/promo', 'WRITE', NOW()),

-- 报表查看
(120, 'report:sales', '销售报表', '/report', 'READ', NOW()),
(121, 'report:inventory', '库存报表', '/report', 'READ', NOW()),
(122, 'report:finance', '财务报表', '/report', 'READ', NOW());

-- 为角色分配权限
-- STORE_MANAGER（门店店长）
INSERT INTO role_permission (role_id, permission_id) VALUES
(2, 1), (2, 30), (2, 40), (2, 50), (2, 51), (2, 52), (2, 60), (2, 61), (2, 62), (2, 120);

-- CASHIER（收银员）
INSERT INTO role_permission (role_id, permission_id) VALUES
(3, 50), (3, 51), (3, 60), (3, 63);

-- WAREHOUSE（仓库管理员）
INSERT INTO role_permission (role_id, permission_id) VALUES
(4, 30), (4, 40), (4, 41), (4, 42), (4, 73), (4, 121);

-- PURCHASER（采购员）
INSERT INTO role_permission (role_id, permission_id) VALUES
(5, 30), (5, 70), (5, 71), (5, 73);

-- PRODUCTION（生产计划员）
INSERT INTO role_permission (role_id, permission_id) VALUES
(6, 30), (6, 40), (6, 80), (6, 81), (6, 82), (6, 83), (6, 90);

-- WORKER（生产工人）
INSERT INTO role_permission (role_id, permission_id) VALUES
(7, 90), (7, 91);

-- FINANCE（财务人员）
INSERT INTO role_permission (role_id, permission_id) VALUES
(8, 50), (8, 70), (8, 100), (8, 101), (8, 120), (8, 121), (8, 122);

-- 启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

SELECT CONCAT('初始化完成，共 ', COUNT(*), ' 个权限点') AS result FROM permission;
