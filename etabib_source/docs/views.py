from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import Http404
import os
import markdown

@login_required
def index(request):
    """Documentation home page"""
    context = {
        'title': 'eTabib Documentation',
        'sections': [
            {
                'name': 'Vue d\'Ensemble',
                'icon': '🎯',
                'docs': [
                    {'title': 'Architecture', 'url': 'platform-architecture'},
                    {'title': 'Services', 'url': 'service-map'},
                    {'title': 'Glossaire', 'url': 'glossary'},
                ]
            },
            {
                'name': 'Business',
                'icon': '💼',
                'docs': [
                    {'title': 'Résumé Exécutif', 'url': 'executive-summary'},
                    {'title': 'Processus', 'url': 'business-processes'},
                    {'title': 'KPIs', 'url': 'kpis-and-metrics'},
                    {'title': 'Conformité', 'url': 'compliance-and-regulations'},
                ]
            },
            {
                'name': 'Opérations',
                'icon': '⚙️',
                'docs': [
                    {'title': 'Déploiement', 'url': 'deployment-guide'},
                    {'title': 'Sauvegarde', 'url': 'backup-and-recovery'},
                    {'title': 'Monitoring', 'url': 'monitoring-and-alerts'},
                ]
            },
            {
                'name': 'Développement',
                'icon': '💻',
                'docs': [
                    {'title': 'Base de Données', 'url': 'database-schema'},
                    {'title': 'API', 'url': 'api-specifications'},
                    {'title': 'Django', 'url': 'django-application'},
                    {'title': 'Celery', 'url': 'celery-tasks'},
                    {'title': 'Ollama AI', 'url': 'ollama-setup'},
                ]
            },
            {
                'name': 'Données',
                'icon': '📊',
                'docs': [
                    {'title': 'Sync Médicaments', 'url': 'drug-database-sync'},
                    {'title': 'Dictionnaire', 'url': 'data-dictionary'},
                    {'title': 'Qualité', 'url': 'data-quality'},
                ]
            },
            {
                'name': 'Support',
                'icon': '🆘',
                'docs': [
                    {'title': 'Dépannage', 'url': 'troubleshooting-guide'},
                    {'title': 'Problèmes Courants', 'url': 'common-issues'},
                    {'title': 'FAQ', 'url': 'faq'},
                ]
            },
        ]
    }
    return render(request, 'docs/index.html', context)

@login_required
def view_doc(request, doc_slug):
    """View a specific documentation file"""
    doc_map = {
        'platform-architecture': '00-OVERVIEW/platform-architecture.md',
        'service-map': '00-OVERVIEW/service-map.md',
        'glossary': '00-OVERVIEW/glossary.md',
        'executive-summary': '01-BUSINESS/executive-summary.md',
        'business-processes': '01-BUSINESS/business-processes.md',
        'kpis-and-metrics': '01-BUSINESS/kpis-and-metrics.md',
        'compliance-and-regulations': '01-BUSINESS/compliance-and-regulations.md',
        'deployment-guide': '02-OPERATIONS/deployment-guide.md',
        'backup-and-recovery': '02-OPERATIONS/backup-and-recovery.md',
        'monitoring-and-alerts': '02-OPERATIONS/monitoring-and-alerts.md',
        'database-schema': '03-DEVELOPMENT/architecture/database-schema.md',
        'api-specifications': '03-DEVELOPMENT/architecture/api-specifications.md',
        'django-application': '03-DEVELOPMENT/backend/django-application.md',
        'celery-tasks': '03-DEVELOPMENT/backend/celery-tasks.md',
        'ollama-setup': '03-DEVELOPMENT/ai-services/ollama-setup.md',
        'drug-database-sync': '04-DATA/drug-database-sync.md',
        'data-dictionary': '04-DATA/data-dictionary.md',
        'data-quality': '04-DATA/data-quality.md',
        'troubleshooting-guide': '06-SUPPORT/troubleshooting-guide.md',
        'common-issues': '06-SUPPORT/common-issues.md',
        'faq': '06-SUPPORT/faq.md',
    }
    
    if doc_slug not in doc_map:
        raise Http404("Documentation not found")
    
    doc_path = os.path.join('/app/docs/static/docs', doc_map[doc_slug])
    
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc', 'tables'])
        html_content = md.convert(content)
        
        context = {
            'title': doc_slug.replace('-', ' ').title(),
            'content': html_content,
        }
        return render(request, 'docs/viewer.html', context)
    
    except FileNotFoundError:
        raise Http404("Documentation file not found")
