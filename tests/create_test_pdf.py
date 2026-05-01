"""生成 RAG 测试 PDF 文档"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


def create_test_pdf(output_path: str):
    """创建包含表格和结构化数据的测试 PDF"""
    
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 中文字体名称
    chinese_font = 'Helvetica'  # Default
    
    # 尝试注册中文字体
    try:
        # Windows 常见中文字体路径
        font_paths = [
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                chinese_font = 'Chinese'
                styles['Normal'].fontName = 'Chinese'
                styles['Heading1'].fontName = 'Chinese'
                styles['Heading2'].fontName = 'Chinese'
                styles['Title'].fontName = 'Chinese'
                break
    except Exception as e:
        print(f"Warning: Could not load Chinese font: {e}")
    
    story = []
    
    # 标题
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
    )
    story.append(Paragraph("Nova-RAG 测试文档", title_style))
    story.append(Paragraph("本文档用于测试 RAG 系统的检索和生成质量", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # 第一章：公司信息
    story.append(Paragraph("第一章 公司概况", styles['Heading1']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("1.1 公司简介", styles['Heading2']))
    story.append(Paragraph(
        "星辰科技有限公司成立于 2020 年 3 月 15 日，注册资本 5000 万元人民币。"
        "公司总部位于北京市海淀区中关村科技园区，现有员工 350 人。"
        "公司专注于人工智能和大数据领域，主要产品包括智能客服系统、数据分析平台和 RAG 知识库系统。",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("1.2 组织架构", styles['Heading2']))
    story.append(Paragraph(
        "公司设有 5 个核心部门：研发部（150人）、产品部（30人）、市场部（50人）、"
        "运营部（80人）、财务部（40人）。CEO 王明直接管理各部门总监。",
        styles['Normal']
    ))
    story.append(Spacer(1, 20))
    
    # 第二章：产品信息（含表格）
    story.append(Paragraph("第二章 产品线", styles['Heading1']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("2.1 核心产品列表", styles['Heading2']))
    story.append(Paragraph("以下是公司的主要产品及其关键信息：", styles['Normal']))
    story.append(Spacer(1, 10))
    
    # 产品表格
    product_data = [
        ['产品名称', '版本', '发布时间', '用户数', '主要功能'],
        ['智能客服 Pro', 'v3.2.1', '2024-06-15', '50万+', '多轮对话、意图识别、情感分析'],
        ['数据洞察平台', 'v2.0.0', '2024-03-20', '20万+', '数据可视化、预测分析、报表生成'],
        ['RAG 知识库', 'v1.5.0', '2024-09-01', '10万+', '文档检索、智能问答、知识图谱'],
        ['AI 写作助手', 'v1.0.0', '2024-11-15', '5万+', '文章生成、改写润色、多语言翻译'],
    ]
    
    table = Table(product_data, colWidths=[3*cm, 2*cm, 3*cm, 2*cm, 6*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))
    
    # 第三章：技术架构
    story.append(Paragraph("第三章 技术架构", styles['Heading1']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("3.1 技术栈", styles['Heading2']))
    
    # 技术栈表格
    tech_data = [
        ['层级', '技术选型', '说明'],
        ['前端', 'React 18 + TypeScript', '使用 Vite 构建，TailwindCSS 样式'],
        ['后端', 'Python FastAPI', '高性能异步框架，自动 API 文档'],
        ['数据库', 'PostgreSQL + pgvector', '支持向量存储，混合检索'],
        ['向量模型', 'DashScope text-embedding-v3', '1024 维度，支持中英文'],
        ['LLM', 'MiniMax M2.7', '支持 128K 上下文，流式输出'],
        ['缓存', 'Redis', '会话缓存、热点数据'],
    ]
    
    tech_table = Table(tech_data, colWidths=[3*cm, 5*cm, 8*cm])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("3.2 RAG 检索流程", styles['Heading2']))
    story.append(Paragraph(
        "RAG 系统的检索流程包括以下步骤："
        "1) 用户输入查询；2) Query Rewriter 生成多个改写变体；"
        "3) 向量检索和 BM25 检索并行执行；4) RRF 融合两路结果；"
        "5) Cross-Encoder 重排序；6) 返回 Top-K 结果给 LLM 生成回答。",
        styles['Normal']
    ))
    story.append(Spacer(1, 20))
    
    # 第四章：性能指标
    story.append(Paragraph("第四章 性能指标", styles['Heading1']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("4.1 系统性能", styles['Heading2']))
    
    perf_data = [
        ['指标', '目标值', '当前值', '状态'],
        ['API 响应时间', '< 500ms', '320ms', '达标'],
        ['检索召回率', '> 85%', '92%', '达标'],
        ['回答准确率', '> 80%', '87%', '达标'],
        ['并发支持', '> 100 QPS', '150 QPS', '达标'],
        ['系统可用性', '> 99.9%', '99.95%', '达标'],
    ]
    
    perf_table = Table(perf_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 20))
    
    # 第五章：常见问题
    story.append(Paragraph("第五章 常见问题", styles['Heading1']))
    story.append(Spacer(1, 10))
    
    qa_pairs = [
        ("Q: RAG 系统支持哪些文档格式？",
         "A: 目前支持 PDF、DOCX、XLSX、CSV、PPTX、Markdown 和 TXT 格式。"),
        ("Q: 如何提高检索准确率？",
         "A: 可以通过以下方式：1) 使用 @ 提及指定文档范围；2) 优化文档分块策略；3) 调整检索参数。"),
        ("Q: 系统是否支持多语言？",
         "A: 是的，系统支持中英文混合检索，向量模型和 LLM 都具备多语言能力。"),
    ]
    
    for q, a in qa_pairs:
        story.append(Paragraph(q, styles['Heading2']))
        story.append(Paragraph(a, styles['Normal']))
        story.append(Spacer(1, 10))
    
    # 构建 PDF
    doc.build(story)
    print(f"PDF created: {output_path}")


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "rag_test_document.pdf")
    create_test_pdf(output_path)
