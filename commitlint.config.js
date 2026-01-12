module.exports = {
    extends: ['@commitlint/config-conventional'],  // 继承Angular提交规范[9,11](@ref)
    rules: {
        'type-enum': [  // 允许的提交类型[9,11](@ref)
            2,
            'always',
            [
                'feat',     // 新功能[9,10,11](@ref)
                'fix',      // 修复bug[9,10,11](@ref)
                'docs',     // 文档更新[9,10,11](@ref)
                'style',    // 代码格式调整[9,10,11](@ref)
                'refactor', // 代码重构[9,10,11](@ref)
                'test',     // 测试相关[9,10,11](@ref)
                'chore',    // 构建过程或辅助工具变动[9,10,11](@ref)
                'revert'    // 回滚commit[9,11](@ref)
            ]
        ],
        'header-max-length': [2, 'always', 72],  // 提交信息标题最大长度[9](@ref)
        'subject-case': [0, 'never', 'sentence-case']
    }
};