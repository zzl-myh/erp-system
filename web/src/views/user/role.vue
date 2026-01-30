<template>
  <div class="role-container">
    <!-- 头部操作区 -->
    <div class="header-actions">
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增角色
      </el-button>
    </div>

    <!-- 角色列表 -->
    <el-table :data="roleList" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="code" label="角色编码" width="150" />
      <el-table-column prop="name" label="角色名称" width="150" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
          <el-button 
            type="warning" 
            link 
            @click="handlePermission(row)"
            :disabled="row.code === 'ADMIN'"
          >
            配置权限
          </el-button>
          <el-button 
            type="danger" 
            link 
            @click="handleDelete(row)"
            :disabled="row.code === 'ADMIN'"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑角色' : '新增角色'"
      width="500px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="角色编码" prop="code">
          <el-input 
            v-model="formData.code" 
            placeholder="请输入角色编码（如 ADMIN）"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入角色描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 权限配置对话框 -->
    <el-dialog
      v-model="permissionDialogVisible"
      :title="`配置权限 - ${currentPermissionRole?.name || ''}`"
      width="800px"
      destroy-on-close
    >
      <div v-loading="permissionLoading" class="permission-container">
        <div class="permission-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>ADMIN 角色拥有所有权限，无需配置</span>
        </div>
        
        <!-- 按模块分组显示权限 -->
        <div v-for="group in permissionGroups" :key="group.module" class="permission-group">
          <div class="group-header">
            <el-checkbox
              :model-value="isGroupAllChecked(group.permissions)"
              :indeterminate="isGroupIndeterminate(group.permissions)"
              @change="(val: boolean) => handleGroupCheck(group.permissions, val)"
            >
              {{ group.moduleName }}
            </el-checkbox>
          </div>
          <div class="group-content">
            <el-checkbox-group v-model="selectedPermissions">
              <el-checkbox 
                v-for="perm in group.permissions" 
                :key="perm.code" 
                :label="perm.code"
                :value="perm.code"
              >
                {{ perm.name }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="permissionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handlePermissionSubmit" :loading="permissionSubmitLoading">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, InfoFilled } from '@element-plus/icons-vue'
import { 
  getRoleList, createRole, updateRole, deleteRole, 
  getPermissionList, getRolePermissions, assignRolePermissions,
  type Role, type RoleCreate, type RoleUpdate, type Permission 
} from '@/api/user'

// 状态
const loading = ref(false)
const roleList = ref<Role[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const currentRole = ref<Role | null>(null)

// 权限配置状态
const permissionDialogVisible = ref(false)
const permissionLoading = ref(false)
const permissionSubmitLoading = ref(false)
const currentPermissionRole = ref<Role | null>(null)
const allPermissions = ref<Permission[]>([])
const selectedPermissions = ref<string[]>([])

// 模块名称映射
const moduleNameMap: Record<string, string> = {
  'user': '用户管理',
  'role': '角色管理',
  'org': '组织管理',
  'item': '商品管理',
  'stock': '库存管理',
  'order': '订单管理',
  'purchase': '采购管理',
  'production': '生产管理',
  'member': '会员管理',
  'report': '报表管理',
  'promo': '促销管理',
  'system': '系统管理'
}

// 按模块分组权限
const permissionGroups = computed(() => {
  const groups: { module: string; moduleName: string; permissions: Permission[] }[] = []
  const moduleMap = new Map<string, Permission[]>()
  
  allPermissions.value.forEach((perm: Permission) => {
    const module = perm.code.split(':')[0]
    if (!moduleMap.has(module)) {
      moduleMap.set(module, [])
    }
    moduleMap.get(module)!.push(perm)
  })
  
  moduleMap.forEach((permissions, module) => {
    groups.push({
      module,
      moduleName: moduleNameMap[module] || module,
      permissions
    })
  })
  
  return groups
})

// 检查分组是否全选
function isGroupAllChecked(permissions: Permission[]): boolean {
  return permissions.every(p => selectedPermissions.value.includes(p.code))
}

// 检查分组是否半选
function isGroupIndeterminate(permissions: Permission[]): boolean {
  const checkedCount = permissions.filter(p => selectedPermissions.value.includes(p.code)).length
  return checkedCount > 0 && checkedCount < permissions.length
}

// 分组全选/取消全选
function handleGroupCheck(permissions: Permission[], checked: boolean) {
  const codes = permissions.map(p => p.code)
  if (checked) {
    // 添加该组所有权限
    const newSelected = [...selectedPermissions.value]
    codes.forEach(code => {
      if (!newSelected.includes(code)) {
        newSelected.push(code)
      }
    })
    selectedPermissions.value = newSelected
  } else {
    // 移除该组所有权限
    selectedPermissions.value = selectedPermissions.value.filter((code: string) => !codes.includes(code))
  }
}

// 表单数据
const formData = reactive<RoleCreate>({
  code: '',
  name: '',
  description: ''
})

// 表单校验规则
const formRules: FormRules = {
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    { pattern: /^[A-Z_]+$/, message: '只能包含大写字母和下划线', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' }
  ]
}

// 获取角色列表
async function fetchList() {
  loading.value = true
  try {
    const res = await getRoleList()
    if (res.success) {
      roleList.value = res.data || []
    } else {
      ElMessage.error(res.message || '获取角色列表失败')
    }
  } catch (error) {
    ElMessage.error('获取角色列表失败')
  } finally {
    loading.value = false
  }
}

// 重置表单
function resetForm() {
  formData.code = ''
  formData.name = ''
  formData.description = ''
  currentRole.value = null
}

// 新增角色
function handleAdd() {
  resetForm()
  isEdit.value = false
  dialogVisible.value = true
}

// 编辑角色
function handleEdit(row: Role) {
  currentRole.value = row
  isEdit.value = true
  formData.code = row.code
  formData.name = row.name
  formData.description = row.description || ''
  dialogVisible.value = true
}

// 配置权限
async function handlePermission(row: Role) {
  currentPermissionRole.value = row
  permissionDialogVisible.value = true
  permissionLoading.value = true
  
  try {
    // 并行加载所有权限和角色已有权限
    const [permRes, rolePermRes] = await Promise.all([
      getPermissionList(),
      getRolePermissions(row.id)
    ])
    
    if (permRes.success) {
      allPermissions.value = permRes.data || []
    } else {
      ElMessage.error(permRes.message || '获取权限列表失败')
    }
    
    if (rolePermRes.success) {
      selectedPermissions.value = rolePermRes.data || []
    } else {
      selectedPermissions.value = []
    }
  } catch (error) {
    ElMessage.error('加载权限信息失败')
  } finally {
    permissionLoading.value = false
  }
}

// 提交权限配置
async function handlePermissionSubmit() {
  if (!currentPermissionRole.value) return
  
  permissionSubmitLoading.value = true
  try {
    const res = await assignRolePermissions({
      role_id: currentPermissionRole.value.id,
      permission_codes: selectedPermissions.value
    })
    
    if (res.success) {
      ElMessage.success('权限配置成功')
      permissionDialogVisible.value = false
    } else {
      ElMessage.error(res.message || '权限配置失败')
    }
  } catch (error) {
    ElMessage.error('权限配置失败')
  } finally {
    permissionSubmitLoading.value = false
  }
}

// 删除角色
async function handleDelete(row: Role) {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色 "${row.name}" 吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    const res = await deleteRole(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchList()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    // 用户取消
  }
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitLoading.value = true

    if (isEdit.value && currentRole.value) {
      // 编辑
      const updateData: RoleUpdate = {
        name: formData.name,
        description: formData.description
      }
      const res = await updateRole(currentRole.value.id, updateData)
      if (res.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        fetchList()
      } else {
        ElMessage.error(res.message || '更新失败')
      }
    } else {
      // 新增
      const res = await createRole(formData)
      if (res.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        fetchList()
      } else {
        ElMessage.error(res.message || '创建失败')
      }
    }
  } catch (error) {
    // 校验失败
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.role-container {
  padding: 20px;
}

.header-actions {
  margin-bottom: 16px;
}

.permission-container {
  max-height: 500px;
  overflow-y: auto;
}

.permission-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  margin-bottom: 16px;
  background-color: #fdf6ec;
  border-radius: 4px;
  color: #e6a23c;
  font-size: 14px;
}

.permission-group {
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.group-header {
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  font-weight: 500;
}

.group-content {
  padding: 16px;
}

.group-content .el-checkbox {
  margin-right: 24px;
  margin-bottom: 8px;
}
</style>
