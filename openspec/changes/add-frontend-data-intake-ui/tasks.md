## Tasks

### Phase 1: API 类型扩展

- [ ] **T1.1** — 扩展 `src/lib/api-types.ts`
  ```typescript
  interface FileUploadState { ... }
  interface SchemaInferResult { ... }
  interface FieldMapping { ... }
  interface QualityIssue { ... }
  ```

### Phase 2: 组件实现

- [ ] **T2.1** — `src/features/data-intake/data-intake-page.tsx`
  - 页面布局，组合子组件

- [ ] **T2.2** — `src/features/data-intake/file-upload-zone.tsx`
  - 拖拽上传、点击上传、进度显示

- [ ] **T2.3** — `src/features/data-intake/file-list.tsx`
  - 已上传文件列表

- [ ] **T2.4** — `src/features/data-intake/schema-infer-panel.tsx`
  - 字段识别结果展示

- [ ] **T2.5** — `src/features/data-intake/field-mapping-table.tsx`
  - 可编辑字段映射表格

- [ ] **T2.6** — `src/features/data-intake/data-quality-report.tsx`
  - 数据质量报告

### Phase 3: 页面路由

- [ ] **T3.1** — 确保 `src/app/projects/[project_id]/data-intake/page.tsx` 渲染 DataIntakePage

### Phase 4: 验收测试

- [ ] **T4.1** — 上传 CSV 文件成功
- [ ] **T4.2** — 字段映射表格可编辑并保存
- [ ] **T4.3** — 数据质量报告正确显示

---

## 验收标准

1. FileUploadZone 支持拖拽上传
2. schema 推断结果正确显示
3. 字段映射表格可编辑
4. 数据质量报告正确展示 issues
5. Apply 后 project state 更新
