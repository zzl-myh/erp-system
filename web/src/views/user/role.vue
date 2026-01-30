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
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getRoleList, createRole, updateRole, deleteRole, type Role, type RoleCreate, type RoleUpdate } from '@/api/user'

// 状态
const loading = ref(false)
const roleList = ref<Role[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const currentRole = ref<Role | null>(null)

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
</style>
