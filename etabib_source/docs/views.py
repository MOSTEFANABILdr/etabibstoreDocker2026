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
                    {'title': 'Roadmap', 'url': 'roadmap', 'badge': 'NEW'},
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
                    {'title': 'Performance', 'url': 'performance-tuning', 'badge': 'NEW'},
                    {'title': 'Logging', 'url': 'logging-policy', 'badge': 'NEW'},
                    {'title': 'Monitoring', 'url': 'monitoring-and-alerts'},
                ]
            },
            {
                'name': 'Développement',
                'icon': '💻',
                'docs': [
                    {'title': 'Architecture Système', 'url': 'system-design'},
                    {'title': 'Web App', 'url': 'web-app-usage', 'badge': 'NEW'},
                    {'title': 'Desktop App', 'url': 'desktop-app-architecture', 'badge': 'NEW'},
                    {'title': 'Base de Données', 'url': 'database-schema'},
                    {'title': 'API', 'url': 'api-specifications'},
                    {'title': 'Environment Local', 'url': 'local-environment', 'badge': 'NEW'},
                    {'title': 'Tests', 'url': 'testing-guidelines', 'badge': 'NEW'},
                    {'title': 'Integartion Jitsi', 'url': 'jitsi-meet', 'badge': 'NEW'},
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
                'name': 'Sécurité',
                'icon': '🔒',
                'docs': [
                    {'title': 'Authentification', 'url': 'authentication'},
                    {'title': 'Politique Sécurité', 'url': 'security-policy', 'badge': 'NEW'},
                    {'title': 'Contrôle d\'Accès (RBAC)', 'url': 'access-control', 'badge': 'NEW'},
                    {'title': 'Vulnérabilités', 'url': 'vulnerability-management', 'badge': 'NEW'},
                ]
            },
            {
                'name': 'Runbooks',
                'icon': '📖',
                'docs': [
                    {'title': 'Onboarding Client', 'url': 'new-client-onboarding', 'badge': 'NEW'},
                    {'title': 'Mises à jour (Release)', 'url': 'feature-release', 'badge': 'NEW'},
                    {'title': 'Urgence', 'url': 'emergency-procedures'},
                    {'title': 'Restart Services', 'url': 'service-restart'},
                    {'title': 'Maintenance BDD', 'url': 'database-maintenance'},
                    {'title': 'SSL', 'url': 'ssl-renewal'},
                ]
            },
            {
                'name': 'Support',
                'icon': '🆘',
                'docs': [
                    {'title': 'Formation', 'url': 'training-materials', 'badge': 'NEW'},
                    {'title': 'SLAs', 'url': 'sla-definitions', 'badge': 'NEW'},
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
        # OVERVIEW
        'platform-architecture': '00-OVERVIEW/platform-architecture.md',
        'service-map': '00-OVERVIEW/service-map.md',
        'glossary': '00-OVERVIEW/glossary.md',
        
        # BUSINESS
        'executive-summary': '01-BUSINESS/executive-summary.md',
        'roadmap': '01-BUSINESS/roadmap.md',
        'business-processes': '01-BUSINESS/business-processes.md',
        'kpis-and-metrics': '01-BUSINESS/kpis-and-metrics.md',
        'compliance-and-regulations': '01-BUSINESS/compliance-and-regulations.md',
        
        # OPERATIONS
        'deployment-guide': '02-OPERATIONS/deployment-guide.md',
        'backup-and-recovery': '02-OPERATIONS/backup-and-recovery.md',
        'performance-tuning': '02-OPERATIONS/performance-tuning.md',
        'logging-policy': '02-OPERATIONS/logging-policy.md',
        'monitoring-and-alerts': '02-OPERATIONS/monitoring-and-alerts.md',
        
        # DEVELOPMENT
        'system-design': '03-DEVELOPMENT/architecture/system-design.md',
        'web-app-usage': '03-DEVELOPMENT/frontend/web-app-usage.md',
        'desktop-app-architecture': '03-DEVELOPMENT/frontend/desktop-app-architecture.md',
        'database-schema': '03-DEVELOPMENT/architecture/database-schema.md',
        'api-specifications': '03-DEVELOPMENT/architecture/api-specifications.md',
        'local-environment': '03-DEVELOPMENT/setup/local-environment.md',
        'testing-guidelines': '03-DEVELOPMENT/testing/testing-guidelines.md',
        'jitsi-meet': '03-DEVELOPMENT/integrations/jitsi-meet.md',
        'django-application': '03-DEVELOPMENT/backend/django-application.md',
        'celery-tasks': '03-DEVELOPMENT/backend/celery-tasks.md',
        'ollama-setup': '03-DEVELOPMENT/ai-services/ollama-setup.md',
        
        # DATA
        'drug-database-sync': '04-DATA/drug-database-sync.md',
        'data-dictionary': '04-DATA/data-dictionary.md',
        'data-quality': '04-DATA/data-quality.md',
        
        # SECURITY
        'authentication': '05-SECURITY/authentication.md',
        'security-policy': '05-SECURITY/security-policy.md',
        'access-control': '05-SECURITY/access-control.md',
        'vulnerability-management': '05-SECURITY/vulnerability-management.md',
        
        # SUPPORT
        'training-materials': '06-SUPPORT/training-materials.md',
        'sla-definitions': '06-SUPPORT/sla-definitions.md',
        'troubleshooting-guide': '06-SUPPORT/troubleshooting-guide.md',
        'common-issues': '06-SUPPORT/common-issues.md',
        'faq': '06-SUPPORT/faq.md',

        # RUNBOOKS
        'new-client-onboarding': '07-RUNBOOKS/new-client-onboarding.md',
        'feature-release': '07-RUNBOOKS/feature-release.md',
        'emergency-procedures': '07-RUNBOOKS/emergency-procedures.md',
        'service-restart': '07-RUNBOOKS/service-restart.md',
        'database-maintenance': '07-RUNBOOKS/database-maintenance.md',
        'ssl-renewal': '07-RUNBOOKS/ssl-renewal.md',
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
        raise Http404(f"Documentation file not found: {doc_map[doc_slug]}")
