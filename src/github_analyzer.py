import requests
import csv
from datetime import datetime
import os
from dotenv import load_dotenv
import statistics
import time

# Carregar variáveis de ambiente
load_dotenv()

class GitHubAnalyzerMVP:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("Configure GITHUB_TOKEN no arquivo .env")
        
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.graphql_url = 'https://api.github.com/graphql'

    def create_query(self, cursor=None):
        """Query GraphQL com suporte a paginação"""
        after_cursor = f', after: "{cursor}"' if cursor else ''
        
        return f"""
        query {{
          search(query: "stars:>1000 sort:stars-desc", type: REPOSITORY, first: 10{after_cursor}) {{
            edges {{
              node {{
                ... on Repository {{
                  name
                  owner {{
                    login
                  }}
                  createdAt
                  updatedAt
                  stargazerCount
                  primaryLanguage {{
                    name
                  }}
                  pullRequests(states: MERGED) {{
                    totalCount
                  }}
                  releases {{
                    totalCount
                  }}
                  issues {{
                    totalCount
                  }}
                  closedIssues: issues(states: CLOSED) {{
                    totalCount
                  }}
                  url
                }}
              }}
            }}
            pageInfo {{
              endCursor
              hasNextPage
            }}
          }}
        }}
        """

    def fetch_repositories(self):
        """Faz 10 requisições de 10 repositórios cada para buscar 100 total"""
        print("🔄 Buscando 100 repositórios mais populares (10 páginas de 10)...")
        
        all_repositories = []
        cursor = None
        page = 1
        max_pages = 10  # 10 páginas de 10 = 100 repositórios
        
        while page <= max_pages:
            print(f"📄 Página {page}/10 - Buscando repositórios {(page-1)*10 + 1}-{page*10}...")
            
            query = self.create_query(cursor)
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json={'query': query}
            )
            
            if response.status_code != 200:
                raise Exception(f"Erro na requisição página {page}: {response.status_code} - {response.text}")
            
            data = response.json()
            
            if 'errors' in data:
                raise Exception(f"Erro GraphQL página {page}: {data['errors']}")
            
            # Adicionar repositórios desta página à lista total
            edges = data['data']['search']['edges']
            all_repositories.extend(edges)
            
            print(f"   ✅ {len(edges)} repositórios coletados (Total: {len(all_repositories)})")
            
            # Verificar se há próxima página
            page_info = data['data']['search']['pageInfo']
            if not page_info['hasNextPage'] or len(all_repositories) >= 100:
                print(f"🏁 Paginação finalizada na página {page}")
                break
            
            # Configurar cursor para próxima página
            cursor = page_info['endCursor']
            page += 1
            
            # Rate limiting - pequena pausa entre requisições
            time.sleep(0.5)  # 500ms entre requisições
        
        print(f"✅ Total coletado: {len(all_repositories)} repositórios")
        return all_repositories

    def calculate_age_days(self, created_at):
        """RQ01: Calcula idade do repositório em dias"""
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        return (datetime.now(created_date.tzinfo) - created_date).days

    def calculate_days_since_update(self, updated_at):
        """RQ04: Calcula dias desde última atualização"""
        updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        return (datetime.now(updated_date.tzinfo) - updated_date).days

    def process_repositories(self, edges):
        """Processa dados dos repositórios e calcula métricas das RQs"""
        repositories = []
        
        print("📊 Processando dados e calculando métricas das RQs...")
        
        for i, edge in enumerate(edges, 1):
            repo = edge['node']
            
            # RQ01: Idade do repositório
            age_days = self.calculate_age_days(repo['createdAt'])
            
            # RQ02: Pull requests aceitas (merged)
            merged_prs = repo['pullRequests']['totalCount']
            
            # RQ03: Total de releases
            total_releases = repo['releases']['totalCount']
            
            # RQ04: Dias desde última atualização
            days_since_update = self.calculate_days_since_update(repo['updatedAt'])
            
            # RQ05: Linguagem primária
            primary_language = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else 'Unknown'
            
            # RQ06: Percentual de issues fechadas
            total_issues = repo['issues']['totalCount']
            closed_issues = repo['closedIssues']['totalCount']
            closed_issues_percentage = (closed_issues / total_issues * 100) if total_issues > 0 else 0
            
            repo_data = {
                'name': repo['name'],
                'owner': repo['owner']['login'],
                'url': repo['url'],
                'stars': repo['stargazerCount'],
                'age_days': age_days,
                'merged_pull_requests': merged_prs,
                'total_releases': total_releases,
                'days_since_last_update': days_since_update,
                'primary_language': primary_language,
                'total_issues': total_issues,
                'closed_issues': closed_issues,
                'closed_issues_percentage': round(closed_issues_percentage, 2)
            }
            
            repositories.append(repo_data)
            
            # Progress indicator
            if i % 25 == 0:
                print(f"   ✅ Processados {i}/{len(edges)} repositórios")
        
        return repositories

    def save_to_csv(self, repositories, filename='repositories_data.csv'):
        """Salva dados em CSV"""
        fieldnames = [
            'name', 'owner', 'url', 'stars', 
            'age_days', 'merged_pull_requests', 'total_releases',
            'days_since_last_update', 'primary_language',
            'total_issues', 'closed_issues', 'closed_issues_percentage'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(repositories)
        
        print(f"💾 Dados salvos em: {filename}")

    def print_summary(self, repositories):
        """Mostra resumo básico dos dados coletados"""
        print(f"\n{'='*50}")
        print(f"📊 RESUMO DOS DADOS COLETADOS")
        print(f"{'='*50}")
        print(f"Total de repositórios: {len(repositories)}")
        
        # RQ01 - Idade
        ages = [repo['age_days'] for repo in repositories]
        print(f"\nRQ01 - Estatísticas das idades dos repositórios:")
        print(f"  Média: {statistics.mean(ages):.2f} dias")
        print(f"  Mediana: {statistics.median(ages)} dias")
        try:
            print(f"  Moda: {statistics.mode(ages)} dias")
        except statistics.StatisticsError:
            print(f"  Moda: Não há valor único mais comum")
        
        # RQ02 - Pull Requests aceitas
        prs = [repo['merged_pull_requests'] for repo in repositories]
        print(f"\nRQ02 - Pull Requests aceitas:")
        print(f"  Mediana: {statistics.median(prs)}")
        print(f"  Média: {statistics.mean(prs):.2f}")
        try:
            print(f"  Moda: {statistics.mode(prs)}")
        except statistics.StatisticsError:
            print(f"  Moda: Não há valor único mais comum")

        # RQ03 - Releases
        releases = [repo['total_releases'] for repo in repositories]
        print(f"\nRQ03 - Total de releases:")
        print(f"  Mediana: {statistics.median(releases)}")
        print(f"  Média: {statistics.mean(releases):.2f}")
        try:
            print(f"  Moda: {statistics.mode(releases)}")
        except statistics.StatisticsError:
            print(f"  Moda: Não há valor único mais comum")
        print(f"  Repositórios sem releases: {sum(1 for r in releases if r == 0)}")

        # RQ04 - Última atualização
        updates = [repo['days_since_last_update'] for repo in repositories]
        print(f"\nRQ04 - Dias desde última atualização:")
        print(f"  Mediana: {statistics.median(updates)} dias")
        print(f"  Média: {statistics.mean(updates):.2f} dias")
        try:
            print(f"  Moda: {statistics.mode(updates)} dias")
        except statistics.StatisticsError:
            print(f"  Moda: Não há valor único mais comum")
        print(f"  Atualizados recentemente (≤30 dias): {sum(1 for u in updates if u <= 30)} repos")

        # RQ05 - Linguagens
        languages = {}
        for repo in repositories:
            lang = repo['primary_language']
            languages[lang] = languages.get(lang, 0) + 1

        print(f"\nRQ05 - Linguagens mais populares:")
        top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        for lang, count in top_langs:
            print(f"  {lang}: {count} repositórios")

        # RQ06 - Issues fechadas
        closed_percentages = [repo['closed_issues_percentage'] for repo in repositories]
        print(f"\nRQ06 - Issues fechadas:")
        print(f"  Percentual mediano: {statistics.median(closed_percentages):.2f}%")
        print(f"  Percentual médio: {statistics.mean(closed_percentages):.2f}%")
        try:
            print(f"  Moda: {statistics.mode(closed_percentages)}%")
        except statistics.StatisticsError:
            print(f"  Moda: Não há valor único mais comum")
        print(f"  100% fechadas: {sum(1 for repo in repositories if repo['closed_issues_percentage'] == 100)} repos")
                
        print(f"\n{'='*50}")

def main():
    """Função principal do MVP - Lab01S01"""
    print("🚀 GitHub Analyzer MVP - Lab01S01")
    print("Objetivo: Coletar 100 repositórios mais populares")
    print("Métricas: RQ01-RQ06\n")
    
    try:
        # Verificar se arquivo .env existe
        if not os.path.exists('.env'):
            print("❌ Arquivo .env não encontrado!")
            print("💡 Crie um arquivo .env com: GITHUB_TOKEN=seu_token_aqui")
            return
        
        # Inicializar analisador
        analyzer = GitHubAnalyzerMVP()
        
        # Buscar repositórios
        edges = analyzer.fetch_repositories()
        print(f"✅ {len(edges)} repositórios encontrados")
        
        # Processar dados
        repositories = analyzer.process_repositories(edges)
        print(f"✅ {len(repositories)} repositórios processados")
        
        # Salvar em CSV
        analyzer.save_to_csv(repositories)
        
        # Mostrar resumo
        analyzer.print_summary(repositories)
        
        print("\n🎉 Lab01S01 concluído com sucesso!")
        print("📈 Dados prontos para análise das RQs")
        
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")
        print("💡 Verifique se o token GitHub está configurado no arquivo .env")
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("💡 Verifique sua conexão e token GitHub")

if __name__ == "__main__":
    main()