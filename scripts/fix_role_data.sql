-- 修复角色表中文数据
-- 执行方式: docker exec -i erp-mysql-1 mysql -uroot -pX7kL9mP2qR5tlyzm erp < scripts/fix_role_data.sql

-- 更新角色数据
UPDATE role SET name = '系统管理员', description = '拥有全部权限' WHERE code = 'ADMIN';
UPDATE role SET name = '门店店长', description = '门店管理、销售、库存查询' WHERE code = 'STORE_MANAGER';
UPDATE role SET name = '收银员', description = 'POS收银、会员查询' WHERE code = 'CASHIER';
UPDATE role SET name = '仓库管理员', description = '库存管理、采购收货' WHERE code = 'WAREHOUSE';
UPDATE role SET name = '采购员', description = '采购订单管理' WHERE code = 'PURCHASER';
UPDATE role SET name = '生产计划员', description = '生产订单、BOM管理' WHERE code = 'PRODUCTION';
UPDATE role SET name = '生产工人', description = '报工' WHERE code = 'WORKER';
UPDATE role SET name = '财务人员', description = '成本查询、报表' WHERE code = 'FINANCE';

SELECT id, code, name, description FROM role;
