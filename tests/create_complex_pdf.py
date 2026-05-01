"""Generate a complex English PDF document for RAG testing."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, ListFlowable, ListItem
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
import os


def create_charts():
    """Create sample charts for the document."""
    charts = []
    
    # Bar chart - Revenue by Product
    d = Drawing(400, 200)
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 30
    bc.height = 125
    bc.width = 300
    bc.data = [[120, 180, 250, 200]]
    bc.categoryAxis.categoryNames = ['Product A', 'Product B', 'Product C', 'Product D']
    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 300
    bc.valueAxis.valueStep = 50
    bc.bars[0].fillColor = colors.HexColor('#4472C4')
    d.add(bc)
    d.add(String(200, 180, 'Revenue by Product (2024)', fontSize=12, fillColor=colors.black))
    charts.append(d)
    
    # Pie chart - Market Share
    d2 = Drawing(400, 200)
    pc = Pie()
    pc.x = 100
    pc.y = 20
    pc.width = 150
    pc.height = 150
    pc.data = [35, 25, 20, 15, 5]
    pc.labels = ['Cloud Services', 'AI Solutions', 'Data Analytics', 'Consulting', 'Other']
    pc.slices[0].fillColor = colors.HexColor('#4472C4')
    pc.slices[1].fillColor = colors.HexColor('#ED7D31')
    pc.slices[2].fillColor = colors.HexColor('#A5A5A5')
    pc.slices[3].fillColor = colors.HexColor('#FFC000')
    pc.slices[4].fillColor = colors.HexColor('#5B9BD5')
    d2.add(pc)
    d2.add(String(200, 180, 'Market Share Distribution', fontSize=12, fillColor=colors.black))
    charts.append(d2)
    
    return charts


def create_architecture_diagram():
    """Create a simple architecture diagram."""
    d = Drawing(500, 300)
    
    # Background
    d.add(Rect(0, 0, 500, 300, fillColor=colors.white, strokeColor=colors.grey))
    
    # Title
    d.add(String(200, 275, 'System Architecture', fontSize=14, fillColor=colors.black))
    
    # Frontend layer
    d.add(Rect(50, 200, 120, 50, fillColor=colors.HexColor('#4472C4'), strokeColor=colors.black))
    d.add(String(75, 220, 'Frontend', fontSize=10, fillColor=colors.white))
    d.add(String(75, 205, 'React + TS', fontSize=8, fillColor=colors.white))
    
    # API Gateway
    d.add(Rect(200, 200, 120, 50, fillColor=colors.HexColor('#ED7D31'), strokeColor=colors.black))
    d.add(String(225, 220, 'API Gateway', fontSize=10, fillColor=colors.white))
    d.add(String(225, 205, 'FastAPI', fontSize=8, fillColor=colors.white))
    
    # Services
    d.add(Rect(350, 200, 120, 50, fillColor=colors.HexColor('#70AD47'), strokeColor=colors.black))
    d.add(String(375, 220, 'Services', fontSize=10, fillColor=colors.white))
    d.add(String(375, 205, 'Microservices', fontSize=8, fillColor=colors.white))
    
    # Database layer
    d.add(Rect(50, 100, 120, 50, fillColor=colors.HexColor('#5B9BD5'), strokeColor=colors.black))
    d.add(String(75, 120, 'PostgreSQL', fontSize=10, fillColor=colors.white))
    d.add(String(75, 105, '+ pgvector', fontSize=8, fillColor=colors.white))
    
    d.add(Rect(200, 100, 120, 50, fillColor=colors.HexColor('#FFC000'), strokeColor=colors.black))
    d.add(String(225, 120, 'Redis', fontSize=10, fillColor=colors.black))
    d.add(String(225, 105, 'Cache', fontSize=8, fillColor=colors.black))
    
    d.add(Rect(350, 100, 120, 50, fillColor=colors.HexColor('#A5A5A5'), strokeColor=colors.black))
    d.add(String(375, 120, 'MinIO', fontSize=10, fillColor=colors.white))
    d.add(String(375, 105, 'Object Storage', fontSize=8, fillColor=colors.white))
    
    # Arrows
    d.add(Line(110, 200, 110, 150, strokeColor=colors.black))
    d.add(Line(260, 200, 260, 150, strokeColor=colors.black))
    d.add(Line(410, 200, 410, 150, strokeColor=colors.black))
    
    d.add(Line(170, 225, 200, 225, strokeColor=colors.black))
    d.add(Line(320, 225, 350, 225, strokeColor=colors.black))
    
    return d


def create_test_pdf(output_path: str):
    """Create a complex English PDF document for RAG testing."""
    
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=28,
        spaceAfter=30,
        textColor=colors.HexColor('#1F4E79'),
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=20,
        spaceBefore=20,
        spaceAfter=12,
        textColor=colors.HexColor('#2E75B6'),
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor('#4472C4'),
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        spaceAfter=12,
    )
    
    story = []
    
    # ===== COVER PAGE =====
    story.append(Spacer(1, 100))
    story.append(Paragraph("NovaTech Solutions", title_style))
    story.append(Paragraph("Technical Documentation & Architecture Guide", styles['Heading2']))
    story.append(Spacer(1, 50))
    story.append(Paragraph("Version 2.5.0 | January 2025", styles['Normal']))
    story.append(Paragraph("Confidential - Internal Use Only", styles['Normal']))
    story.append(PageBreak())
    
    # ===== TABLE OF CONTENTS =====
    story.append(Paragraph("Table of Contents", heading1_style))
    story.append(Spacer(1, 20))
    
    toc_items = [
        "1. Executive Summary",
        "2. Company Overview",
        "3. Product Portfolio",
        "4. Technical Architecture",
        "5. Data Processing Pipeline",
        "6. Performance Metrics",
        "7. Security Framework",
        "8. Deployment Guide",
        "9. API Reference",
        "10. Troubleshooting",
    ]
    
    for item in toc_items:
        story.append(Paragraph(item, body_style))
    
    story.append(PageBreak())
    
    # ===== CHAPTER 1: EXECUTIVE SUMMARY =====
    story.append(Paragraph("1. Executive Summary", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "NovaTech Solutions is a leading provider of enterprise AI and data analytics platforms. "
        "Founded in 2018, the company has grown to serve over 500 enterprise clients across "
        "15 countries, processing more than 10 petabytes of data annually.",
        body_style
    ))
    
    story.append(Paragraph(
        "This technical documentation provides a comprehensive overview of our platform "
        "architecture, data processing capabilities, and integration guidelines. It serves "
        "as the primary reference for developers, system architects, and technical stakeholders.",
        body_style
    ))
    
    # Key metrics table
    story.append(Spacer(1, 20))
    story.append(Paragraph("Key Performance Indicators", heading2_style))
    
    kpi_data = [
        ['Metric', 'Target', 'Current', 'Status'],
        ['API Response Time', '< 200ms', '145ms', 'PASS'],
        ['System Uptime', '> 99.99%', '99.995%', 'PASS'],
        ['Data Processing', '> 1M records/hr', '1.5M records/hr', 'PASS'],
        ['Query Accuracy', '> 95%', '97.3%', 'PASS'],
        ['Customer Satisfaction', '> 90%', '94.5%', 'PASS'],
    ]
    
    kpi_table = Table(kpi_data, colWidths=[4*cm, 3.5*cm, 3.5*cm, 2*cm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E75B6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#D6E4F0')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#D6E4F0'), colors.HexColor('#E9EFF7')]),
    ]))
    story.append(kpi_table)
    
    story.append(PageBreak())
    
    # ===== CHAPTER 2: COMPANY OVERVIEW =====
    story.append(Paragraph("2. Company Overview", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "NovaTech Solutions was established in San Francisco, California, with a mission "
        "to democratize enterprise AI capabilities. Our leadership team combines decades "
        "of experience in machine learning, distributed systems, and enterprise software.",
        body_style
    ))
    
    story.append(Paragraph("2.1 Organizational Structure", heading2_style))
    
    story.append(Paragraph(
        "The company operates through five strategic divisions, each focused on a specific "
        "aspect of our product ecosystem:",
        body_style
    ))
    
    # Org structure table
    org_data = [
        ['Division', 'Headcount', 'Focus Area', 'Key Products'],
        ['Research & Development', '180', 'AI/ML Innovation', 'NovaLM, NovaVision'],
        ['Engineering', '250', 'Platform Development', 'Cloud Platform, APIs'],
        ['Data Science', '120', 'Analytics & Insights', 'NovaAnalytics, NovaBI'],
        ['Product Management', '45', 'Strategy & Roadmap', 'All Products'],
        ['Customer Success', '85', 'Implementation & Support', 'Professional Services'],
    ]
    
    org_table = Table(org_data, colWidths=[3.5*cm, 2.5*cm, 3.5*cm, 4*cm])
    org_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E9EFF7')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
    ]))
    story.append(org_table)
    
    story.append(Spacer(1, 20))
    
    # Revenue chart
    story.append(Paragraph("2.2 Revenue Distribution", heading2_style))
    charts = create_charts()
    story.append(charts[0])
    
    story.append(PageBreak())
    
    # ===== CHAPTER 3: PRODUCT PORTFOLIO =====
    story.append(Paragraph("3. Product Portfolio", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "NovaTech offers a comprehensive suite of AI-powered products designed to address "
        "the most challenging enterprise data problems. Our product strategy focuses on "
        "three core pillars: Intelligence, Integration, and Insight.",
        body_style
    ))
    
    story.append(Paragraph("3.1 Core Products", heading2_style))
    
    # Products table
    products_data = [
        ['Product', 'Version', 'Release Date', 'Users', 'Key Features'],
        ['NovaLM', 'v4.2.0', '2024-11-15', '200K+', 'LLM, RAG, Fine-tuning'],
        ['NovaAnalytics', 'v3.5.1', '2024-09-20', '150K+', 'Real-time analytics, ML'],
        ['NovaVision', 'v2.8.0', '2024-12-01', '80K+', 'Image recognition, OCR'],
        ['NovaBI', 'v5.1.0', '2024-10-10', '300K+', 'Dashboards, Reports'],
        ['NovaConnect', 'v2.0.0', '2025-01-05', '50K+', 'API Gateway, Integration'],
    ]
    
    products_table = Table(products_data, colWidths=[3*cm, 2*cm, 2.5*cm, 2*cm, 4.5*cm])
    products_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ED7D31')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFF2CC')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFF2CC'), colors.HexColor('#FFFAE6')]),
    ]))
    story.append(products_table)
    
    story.append(Spacer(1, 20))
    
    # Market share chart
    story.append(Paragraph("3.2 Market Position", heading2_style))
    story.append(charts[1])
    
    story.append(PageBreak())
    
    # ===== CHAPTER 4: TECHNICAL ARCHITECTURE =====
    story.append(Paragraph("4. Technical Architecture", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "Our platform is built on a modern microservices architecture designed for "
        "scalability, resilience, and performance. The system processes over 1 million "
        "API requests per minute during peak hours.",
        body_style
    ))
    
    # Architecture diagram
    story.append(Paragraph("4.1 System Architecture Overview", heading2_style))
    story.append(create_architecture_diagram())
    
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("4.2 Technology Stack", heading2_style))
    
    tech_data = [
        ['Layer', 'Technology', 'Purpose'],
        ['Frontend', 'React 18 + TypeScript', 'User interface, SPA'],
        ['Frontend', 'Next.js 14', 'Server-side rendering'],
        ['API Gateway', 'FastAPI (Python)', 'High-performance async API'],
        ['Services', 'Go + gRPC', 'Microservices communication'],
        ['Database', 'PostgreSQL 16', 'Primary data store'],
        ['Database', 'pgvector', 'Vector similarity search'],
        ['Cache', 'Redis 7', 'Session & data caching'],
        ['Queue', 'Apache Kafka', 'Event streaming'],
        ['Storage', 'MinIO', 'S3-compatible object storage'],
        ['ML Platform', 'PyTorch + ONNX', 'Model training & inference'],
        ['Monitoring', 'Prometheus + Grafana', 'Metrics & alerting'],
    ]
    
    tech_table = Table(tech_data, colWidths=[3*cm, 4*cm, 5*cm])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#70AD47')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E2EFDA')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#E2EFDA'), colors.HexColor('#F0F7E8')]),
    ]))
    story.append(tech_table)
    
    story.append(PageBreak())
    
    # ===== CHAPTER 5: DATA PROCESSING PIPELINE =====
    story.append(Paragraph("5. Data Processing Pipeline", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "Our data processing pipeline handles diverse data formats including text, "
        "images, audio, and video. The pipeline processes over 10 petabytes of data "
        "annually with an average latency of 50ms per record.",
        body_style
    ))
    
    story.append(Paragraph("5.1 Document Processing", heading2_style))
    
    story.append(Paragraph(
        "The document processing subsystem supports the following formats:",
        body_style
    ))
    
    formats_list = [
        "PDF - Text extraction, table detection, image extraction",
        "DOCX - Paragraph parsing, style preservation, embedded media",
        "XLSX - Cell extraction, formula evaluation, chart generation",
        "PPTX - Slide content, speaker notes, embedded objects",
        "CSV/TSV - Column detection, data type inference, encoding handling",
        "Images - OCR, object detection, scene understanding",
    ]
    
    for item in formats_list:
        story.append(Paragraph(f"  • {item}", body_style))
    
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("5.2 Chunking Strategy", heading2_style))
    
    chunk_data = [
        ['Strategy', 'Chunk Size', 'Overlap', 'Use Case'],
        ['Recursive Text', '500 chars', '50 chars', 'General documents'],
        ['Semantic', 'Variable', 'Dynamic', 'Technical content'],
        ['Table-aware', 'Per table', 'N/A', 'Structured data'],
        ['Code-aware', 'Per function', '10 lines', 'Source code'],
        ['Image-aware', 'Per image', 'N/A', 'Visual content'],
    ]
    
    chunk_table = Table(chunk_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 4*cm])
    chunk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5B9BD5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#DEEAF6')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
    ]))
    story.append(chunk_table)
    
    story.append(PageBreak())
    
    # ===== CHAPTER 6: PERFORMANCE METRICS =====
    story.append(Paragraph("6. Performance Metrics", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "This section presents detailed performance benchmarks across different "
        "workloads and configurations. All measurements were conducted on our "
        "production environment with real-world data.",
        body_style
    ))
    
    story.append(Paragraph("6.1 API Performance", heading2_style))
    
    perf_data = [
        ['Endpoint', 'Avg Latency', 'P95 Latency', 'P99 Latency', 'Throughput'],
        ['/api/v1/chat', '145ms', '280ms', '450ms', '5000 req/s'],
        ['/api/v1/search', '85ms', '150ms', '220ms', '8000 req/s'],
        ['/api/v1/upload', '320ms', '580ms', '920ms', '2000 req/s'],
        ['/api/v1/analytics', '210ms', '380ms', '550ms', '3500 req/s'],
        ['/api/v1/export', '450ms', '820ms', '1200ms', '1500 req/s'],
    ]
    
    perf_table = Table(perf_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C00000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FCE4EC')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FCE4EC'), colors.HexColor('#FFF0F3')]),
    ]))
    story.append(perf_table)
    
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("6.2 Resource Utilization", heading2_style))
    
    resource_data = [
        ['Resource', 'Capacity', 'Current Usage', 'Peak Usage'],
        ['CPU Cores', '1024', '45%', '78%'],
        ['Memory (RAM)', '4 TB', '52%', '85%'],
        ['Storage (SSD)', '500 TB', '38%', '62%'],
        ['Network', '100 Gbps', '25%', '55%'],
        ['GPU (A100)', '64 units', '68%', '92%'],
    ]
    
    resource_table = Table(resource_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm])
    resource_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7030A0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8D5F5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
    ]))
    story.append(resource_table)
    
    story.append(PageBreak())
    
    # ===== CHAPTER 7: SECURITY FRAMEWORK =====
    story.append(Paragraph("7. Security Framework", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "Security is a fundamental pillar of our platform. We implement defense-in-depth "
        "strategies across all layers of the application stack, ensuring data protection "
        "and compliance with global regulations.",
        body_style
    ))
    
    story.append(Paragraph("7.1 Security Controls", heading2_style))
    
    security_data = [
        ['Layer', 'Control', 'Implementation', 'Status'],
        ['Network', 'WAF + DDoS Protection', 'Cloudflare Enterprise', 'Active'],
        ['Network', 'TLS 1.3', 'All communications', 'Enforced'],
        ['Application', 'OAuth 2.0 + OIDC', 'Multi-provider SSO', 'Active'],
        ['Application', 'RBAC', 'Granular permissions', 'Active'],
        ['Application', 'Input Validation', 'Schema-based', 'Enforced'],
        ['Data', 'AES-256 Encryption', 'At rest + in transit', 'Active'],
        ['Data', 'Data Masking', 'PII/PHI fields', 'Active'],
        ['Infrastructure', 'Container Security', 'Trivy scanning', 'Active'],
        ['Infrastructure', 'Secret Management', 'HashiCorp Vault', 'Active'],
    ]
    
    security_table = Table(security_data, colWidths=[2.5*cm, 3.5*cm, 3.5*cm, 2*cm])
    security_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#D6E4F0')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#D6E4F0'), colors.HexColor('#E9EFF7')]),
    ]))
    story.append(security_table)
    
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("7.2 Compliance Certifications", heading2_style))
    
    compliance_list = [
        "SOC 2 Type II - Service Organization Control",
        "ISO 27001 - Information Security Management",
        "GDPR - General Data Protection Regulation",
        "HIPAA - Health Insurance Portability and Accountability Act",
        "PCI DSS - Payment Card Industry Data Security Standard",
        "FedRAMP - Federal Risk and Authorization Management Program",
    ]
    
    for item in compliance_list:
        story.append(Paragraph(f"  ✓ {item}", body_style))
    
    story.append(PageBreak())
    
    # ===== CHAPTER 8: DEPLOYMENT GUIDE =====
    story.append(Paragraph("8. Deployment Guide", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "This chapter provides step-by-step instructions for deploying the NovaTech "
        "platform in various environments including development, staging, and production.",
        body_style
    ))
    
    story.append(Paragraph("8.1 Prerequisites", heading2_style))
    
    prereq_data = [
        ['Requirement', 'Minimum', 'Recommended', 'Notes'],
        ['CPU', '8 cores', '16+ cores', 'x86_64 architecture'],
        ['Memory', '32 GB', '64+ GB', 'ECC recommended'],
        ['Storage', '500 GB SSD', '2+ TB NVMe', 'RAID 10 for production'],
        ['Network', '1 Gbps', '10+ Gbps', 'Low latency required'],
        ['OS', 'Ubuntu 22.04', 'Ubuntu 24.04 LTS', 'RHEL 9 also supported'],
        ['Docker', '24.0+', '25.0+', 'With BuildKit enabled'],
        ['Kubernetes', '1.28+', '1.30+', 'Helm 3.14+ required'],
    ]
    
    prereq_table = Table(prereq_data, colWidths=[2.5*cm, 2.5*cm, 3*cm, 4*cm])
    prereq_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E9EFF7')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
    ]))
    story.append(prereq_table)
    
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("8.2 Installation Steps", heading2_style))
    
    install_steps = [
        "Step 1: Clone the repository and navigate to the project directory",
        "Step 2: Configure environment variables in .env file",
        "Step 3: Run database migrations using 'nova migrate up'",
        "Step 4: Initialize the vector store with 'nova init vectors'",
        "Step 5: Start the services using 'docker-compose up -d'",
        "Step 6: Verify deployment with 'nova health check'",
    ]
    
    for i, step in enumerate(install_steps, 1):
        story.append(Paragraph(f"  {step}", body_style))
    
    story.append(PageBreak())
    
    # ===== CHAPTER 9: API REFERENCE =====
    story.append(Paragraph("9. API Reference", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "The NovaTech API follows RESTful principles and uses JSON for request/response "
        "bodies. All endpoints require authentication via Bearer token.",
        body_style
    ))
    
    story.append(Paragraph("9.1 Core Endpoints", heading2_style))
    
    api_data = [
        ['Method', 'Endpoint', 'Description', 'Rate Limit'],
        ['POST', '/api/v1/chat/completions', 'Chat with AI assistant', '100/min'],
        ['POST', '/api/v1/embeddings', 'Generate text embeddings', '500/min'],
        ['GET', '/api/v1/documents', 'List documents', '1000/min'],
        ['POST', '/api/v1/documents/upload', 'Upload document', '50/min'],
        ['DELETE', '/api/v1/documents/{id}', 'Delete document', '100/min'],
        ['POST', '/api/v1/search', 'Semantic search', '200/min'],
        ['GET', '/api/v1/analytics', 'Get analytics data', '500/min'],
    ]
    
    api_table = Table(api_data, colWidths=[2*cm, 4.5*cm, 3.5*cm, 2*cm])
    api_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ED7D31')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFF2CC')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFF2CC'), colors.HexColor('#FFFAE6')]),
    ]))
    story.append(api_table)
    
    story.append(PageBreak())
    
    # ===== CHAPTER 10: TROUBLESHOOTING =====
    story.append(Paragraph("10. Troubleshooting", heading1_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "This section provides solutions for common issues encountered during "
        "development and production operations.",
        body_style
    ))
    
    story.append(Paragraph("10.1 Common Issues", heading2_style))
    
    issues = [
        ("Q: How to handle 'Connection refused' errors?",
         "A: Verify that all services are running with 'docker-compose ps'. Check network "
         "configuration and ensure ports are not blocked by firewall."),
        
        ("Q: What to do when vector search returns no results?",
         "A: Ensure the vector store is properly initialized. Run 'nova init vectors --force' "
         "to rebuild the index. Check embedding dimensions match the model configuration."),
        
        ("Q: How to resolve high memory usage?",
         "A: Monitor memory usage with 'nova metrics memory'. Consider increasing the memory "
         "limit in docker-compose.yml or enabling memory swapping for development environments."),
        
        ("Q: Why are API responses slow?",
         "A: Check database connection pool settings. Enable query caching. Review slow query "
         "logs with 'nova logs --slow'. Consider scaling horizontally if needed."),
    ]
    
    for q, a in issues:
        story.append(Paragraph(q, ParagraphStyle(
            'Question',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2E75B6'),
        )))
        story.append(Paragraph(a, body_style))
        story.append(Spacer(1, 10))
    
    # Build PDF
    doc.build(story)
    print(f"PDF created: {output_path}")


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "novatech_documentation.pdf")
    create_test_pdf(output_path)
