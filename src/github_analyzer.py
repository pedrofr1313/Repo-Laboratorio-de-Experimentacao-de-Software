import requests
import json
import csv
from datetime import datetime
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


class GitHubAnalyzer:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("Token GitHub não encontrado. Configure GITHUB_TOKEN no arquivo .env")

        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.graphql_url = 'https://api.github.com/graphql'

    def create_graphql_query(self, cursor=None):
        """
        Cria query GraphQL para buscar os top 100 repositórios mais populares
        Inclui todas as métricas necessárias para as RQs
        """
        after_cursor = f', after: "{cursor}"' if cursor else ''

        query = f"""
        query {{
          search(query: "stars:>1", type: REPOSITORY, first: 100{after_cursor}) {{
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
        return query

    def make_graphql_request(self, query):
        """
        Faz requisição GraphQL para a API do GitHub
        """
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={'query': query}
        )

        if response.status_code != 200:
            raise Exception(f"Erro na requisição: {response.status_code} - {response.text}")

        return response.json()

    def calculate_repository_age(self, created_at):
        """
        Calcula a idade do repositório em dias
        """
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        current_date = datetime.now(created_date.tzinfo)
        return (current_date - created_date).days

    def calculate_days_since_last_update(self, updated_at):
        """
        Calcula quantos dias desde a última atualização
        """
        updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        current_date = datetime.now(updated_date.tzinfo)
        return (current_date - updated_date).days

    def process_repository_data(self, repo):
        """
        Processa os dados de um repositório e calcula as métricas
        """
        # RQ01: Idade do repositório
        age_days = self.calculate_repository_age(repo['createdAt'])

        # RQ02: Pull requests aceitas (merged)
        merged_prs = repo['pullRequests']['totalCount']

        # RQ03: Total de releases
        total_releases = repo['releases']['totalCount']

        # RQ04: Dias desde última atualização
        days_since_update = self.calculate_days_since_last_update(repo['updatedAt'])

        # RQ05: Linguagem primária
        primary_language = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else 'Unknown'

        # RQ06: Percentual de issues fechadas
        total_issues = repo['issues']['totalCount']
        closed_issues = repo['closedIssues']['totalCount']
        closed_issues_ratio = (closed_issues / total_issues * 100) if total_issues > 0 else 0

        return {
            'name': repo['name'],
            'owner': repo['owner']['login'],
            'url': repo['url'],
            'stars': repo['stargazerCount'],
            'created_at': repo['createdAt'],
            'updated_at': repo['updatedAt'],
            'age_days': age_days,  # RQ01
            'merged_pull_requests': merged_prs,  # RQ02
            'total_releases': total_releases,  # RQ03
            'days_since_last_update': days_since_update,  # RQ04
            'primary_language': primary_language,  # RQ05
            'total_issues': total_issues,
            'closed_issues': closed_issues,
            'closed_issues_percentage': round(closed_issues_ratio, 2)  # RQ06
        }

    def fetch_top_repositories(self, limit=1000):
        """
        Busca os top repositórios mais populares com paginação
        Lab01S01: 100 repos | Lab01S02: 1000 repos
        """
        repositories = []
        cursor = None
        page_count = 0
        max_per_request = 100  # Máximo permitido pela API do GitHub

        print(f"Iniciando coleta de {limit} repositórios mais populares...")
        print("🔄 Implementando paginação para grandes volumes de dados...")

        while len(repositories) < limit:
            page_count += 1

            # Calcular quantos repos precisamos nesta requisição
            remaining = limit - len(repositories)
            repos_to_fetch = min(max_per_request, remaining)

            print(f"\n📄 Página {page_count} - Buscando {repos_to_fetch} repositórios...")
            print(f"   Progresso: {len(repositories)}/{limit} repositórios coletados")

            query = self.create_graphql_query_paginated(cursor, repos_to_fetch)

            try:
                result = self.make_graphql_request(query)

                if 'errors' in result:
                    print(f"❌ Erro na query GraphQL: {result['errors']}")
                    # Tentar continuar mesmo com erro
                    if 'data' not in result:
                        break

                # Verificar se temos dados válidos
                if 'data' not in result or 'search' not in result['data']:
                    print("❌ Resposta inválida da API")
                    break

                edges = result['data']['search']['edges']

                if not edges:
                    print("⚠️  Nenhum repositório encontrado nesta página")
                    break

                # Processar repositórios desta página
                repos_processed = 0
                for edge in edges:
                    if len(repositories) >= limit:
                        break

                    try:
                        repo_data = self.process_repository_data(edge['node'])
                        repositories.append(repo_data)
                        repos_processed += 1
                    except Exception as e:
                        print(f"⚠️  Erro ao processar repositório: {e}")
                        continue

                print(f"✅ Processados {repos_processed} repositórios nesta página")

                # Verificar paginação
                page_info = result['data']['search']['pageInfo']

                if not page_info['hasNextPage'] or len(repositories) >= limit:
                    print("🏁 Última página alcançada ou limite atingido")
                    break

                cursor = page_info['endCursor']

                # Rate limiting - pausa entre requisições
                if page_count % 5 == 0:  # A cada 5 páginas
                    print("⏱️  Pausa para rate limiting...")
                    import time
                    time.sleep(2)

            except Exception as e:
                print(f"❌ Erro na requisição da página {page_count}: {e}")
                print("🔄 Tentando continuar...")

                # Tentar continuar com próxima página se possível
                if cursor:
                    continue
                else:
                    break

        print(f"\n🎉 Coleta finalizada!")
        print(f"📊 Total de repositórios coletados: {len(repositories)}")
        print(f"📄 Total de páginas processadas: {page_count}")

        return repositories

    def create_graphql_query_paginated(self, cursor=None, first=100):
        """
        Cria query GraphQL otimizada para paginação
        """
        after_cursor = f', after: "{cursor}"' if cursor else ''

        query = f"""
        query {{
          search(query: "stars:>1", type: REPOSITORY, first: {first}{after_cursor}) {{
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
                  description
                }}
              }}
            }}
            pageInfo {{
              endCursor
              hasNextPage
              startCursor
            }}
            repositoryCount
          }}
        }}
        """
        return query

    def save_to_csv_with_backup(self, repositories, filename='data/repositories_data.csv'):
        """
        Salva os dados em CSV com sistema de backup para grandes volumes
        """
        # Criar diretório data se não existir
        os.makedirs('data', exist_ok=True)

        # Sistema de backup
        backup_filename = filename.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')

        fieldnames = [
            'name', 'owner', 'url', 'stars', 'created_at', 'updated_at',
            'age_days', 'merged_pull_requests', 'total_releases',
            'days_since_last_update', 'primary_language', 'total_issues',
            'closed_issues', 'closed_issues_percentage'
        ]

        # Salvar arquivo principal
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(repositories)

            print(f"✅ Dados salvos em: {filename}")

            # Criar backup
            with open(backup_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(repositories)

            print(f"💾 Backup criado em: {backup_filename}")

        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
            # Tentar salvar pelo menos o backup
            try:
                with open(backup_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(repositories)
                print(f"💾 Dados salvos no backup: {backup_filename}")
            except Exception as backup_error:
                print(f"❌ Erro crítico ao salvar backup: {backup_error}")

    def save_checkpoint(self, repositories, checkpoint_num):
        """
        Salva checkpoint durante a coleta para evitar perda de dados
        """
        filename = f'data/checkpoint_{checkpoint_num}_{len(repositories)}_repos.csv'
        try:
            self.save_to_csv(repositories, filename)
            print(f"💾 Checkpoint salvo: {filename}")
        except Exception as e:
            print(f"⚠️  Erro ao salvar checkpoint: {e}")

    def load_existing_data(self, filename='data/repositories_data.csv'):
        """
        Carrega dados existentes para continuar coleta se necessário
        """
        if os.path.exists(filename):
            try:
                repositories = []
                with open(filename, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        # Converter strings numéricas de volta para int/float
                        row['age_days'] = int(row['age_days'])
                        row['merged_pull_requests'] = int(row['merged_pull_requests'])
                        row['total_releases'] = int(row['total_releases'])
                        row['days_since_last_update'] = int(row['days_since_last_update'])
                        row['total_issues'] = int(row['total_issues'])
                        row['closed_issues'] = int(row['closed_issues'])
                        row['closed_issues_percentage'] = float(row['closed_issues_percentage'])
                        row['stars'] = int(row['stars'])
                        repositories.append(row)

                print(f"📂 Dados existentes carregados: {len(repositories)} repositórios")
                return repositories
            except Exception as e:
                print(f"⚠️  Erro ao carregar dados existentes: {e}")

        return []

    def print_detailed_stats(self, repositories):
        """
        Exibe estatísticas detalhadas dos dados coletados
        """
        total_repos = len(repositories)
        print(f"\n{'=' * 60}")
        print(f"📊 RELATÓRIO DETALHADO - {total_repos} REPOSITÓRIOS")
        print(f"{'=' * 60}")

        # RQ01: Idade dos repositórios
        ages = [repo['age_days'] for repo in repositories]
        ages_sorted = sorted(ages)
        median_age = ages_sorted[len(ages_sorted) // 2]

        print(f"\n🕐 RQ01 - IDADE DOS REPOSITÓRIOS:")
        print(f"   Mediana: {median_age} dias ({median_age / 365:.1f} anos)")
        print(f"   Mais antigo: {max(ages)} dias ({max(ages) / 365:.1f} anos)")
        print(f"   Mais novo: {min(ages)} dias ({min(ages) / 365:.1f} anos)")

        # RQ02: Pull Requests
        prs = [repo['merged_pull_requests'] for repo in repositories]
        prs_sorted = sorted(prs)
        median_prs = prs_sorted[len(prs_sorted) // 2]

        print(f"\n🔄 RQ02 - PULL REQUESTS ACEITAS:")
        print(f"   Mediana: {median_prs}")
        print(f"   Máximo: {max(prs)}")
        print(f"   Repositórios com 0 PRs: {sum(1 for pr in prs if pr == 0)}")

        # RQ03: Releases
        releases = [repo['total_releases'] for repo in repositories]
        releases_sorted = sorted(releases)
        median_releases = releases_sorted[len(releases_sorted) // 2]

        print(f"\n🚀 RQ03 - TOTAL DE RELEASES:")
        print(f"   Mediana: {median_releases}")
        print(f"   Máximo: {max(releases)}")
        print(f"   Repositórios sem releases: {sum(1 for r in releases if r == 0)}")

        # RQ04: Última atualização
        updates = [repo['days_since_last_update'] for repo in repositories]
        updates_sorted = sorted(updates)
        median_update = updates_sorted[len(updates_sorted) // 2]

        print(f"\n🔄 RQ04 - DIAS DESDE ÚLTIMA ATUALIZAÇÃO:")
        print(f"   Mediana: {median_update} dias")
        print(f"   Mais desatualizado: {max(updates)} dias")
        print(f"   Atualizados hoje: {sum(1 for u in updates if u == 0)}")

        # RQ05: Linguagens
        languages = {}
        for repo in repositories:
            lang = repo['primary_language']
            languages[lang] = languages.get(lang, 0) + 1

        print(f"\n💻 RQ05 - LINGUAGENS DE PROGRAMAÇÃO:")
        print(f"   Total de linguagens diferentes: {len(languages)}")
        print(f"   TOP 10 linguagens:")
        for i, (lang, count) in enumerate(sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10], 1):
            percentage = (count / total_repos) * 100
            print(f"     {i:2d}. {lang:<15} {count:4d} repos ({percentage:5.1f}%)")

        # RQ06: Issues fechadas
        issue_ratios = [repo['closed_issues_percentage'] for repo in repositories]
        issue_ratios_sorted = sorted(issue_ratios)
        median_ratio = issue_ratios_sorted[len(issue_ratios_sorted) // 2]

        print(f"\n🐛 RQ06 - PERCENTUAL DE ISSUES FECHADAS:")
        print(f"   Mediana: {median_ratio:.1f}%")
        print(f"   Repositórios com 100% issues fechadas: {sum(1 for r in issue_ratios if r == 100.0)}")
        print(f"   Repositórios sem issues: {sum(1 for repo in repositories if repo['total_issues'] == 0)}")

        # Estatísticas gerais
        total_stars = sum(repo['stars'] for repo in repositories)
        print(f"\n⭐ ESTATÍSTICAS GERAIS:")
        print(f"   Total de estrelas: {total_stars:,}")
        print(
            f"   Estrelas por repositório (mediana): {sorted([r['stars'] for r in repositories])[total_repos // 2]:,}")

        print(f"\n{'=' * 60}")

    def save_to_csv(self, repositories, filename='data/repositories_data.csv'):

        self.save_to_csv_with_backup(repositories, filename)


def main():
    """
    Função principal - Lab01S01 e Lab01S02
    """
    try:
        analyzer = GitHubAnalyzer()

        # Verificar se queremos continuar coleta existente
        existing_data = analyzer.load_existing_data()

        if existing_data and len(existing_data) > 0:
            print(f"🔄 Encontrados {len(existing_data)} repositórios existentes")
            response = input("Deseja continuar a coleta ou recomeçar? (c/r): ").lower()

            if response == 'c':
                print("📊 Continuando com dados existentes...")
                repositories = existing_data
                if len(repositories) >= 1000:
                    print("✅ Coleta já completa!")
                    analyzer.print_detailed_stats(repositories)
                    return
            else:
                print("🔄 Recomeçando coleta...")
                repositories = []
        else:
            repositories = []

        # Determinar quantos repositórios coletar
        if len(repositories) == 0:
            # Lab01S01: Começar com 100
            print("🚀 Lab01S01: Coletando primeiros 100 repositórios...")
            target = 100
        else:
            # Lab01S02: Expandir para 1000
            print("🚀 Lab01S02: Expandindo para 1000 repositórios...")
            target = 1000

        # Coletar dados
        if len(repositories) < target:
            remaining_repos = analyzer.fetch_top_repositories(target)

            # Se estamos continuando, mesclar dados
            if repositories:
                # Evitar duplicatas baseado na URL
                existing_urls = {repo['url'] for repo in repositories}
                new_repos = [repo for repo in remaining_repos if repo['url'] not in existing_urls]
                repositories.extend(new_repos)
                print(f"📊 Mesclados {len(new_repos)} novos repositórios")
            else:
                repositories = remaining_repos

        # Salvar dados com backup
        analyzer.save_to_csv_with_backup(repositories)

        # Checkpoint a cada 200 repositórios
        if len(repositories) >= 200:
            analyzer.save_checkpoint(repositories, "final")

        # Exibir estatísticas detalhadas
        analyzer.print_detailed_stats(repositories)

        # Status do laboratório
        if len(repositories) >= 100 and len(repositories) < 1000:
            print("\n✅ Lab01S01 concluído com sucesso!")
            print("🎯 Próximo passo: Lab01S02 - Execute novamente para coletar 1000 repositórios")
        elif len(repositories) >= 1000:
            print("\n🎉 Lab01S02 concluído com sucesso!")
            print("📈 Pronto para Lab01S03 - Análise e visualização de dados")

        print(f"📁 Dados salvos em: data/repositories_data.csv")

    except KeyboardInterrupt:
        print("\n⏹️  Coleta interrompida pelo usuário")
        print("💾 Dados coletados até agora foram preservados")
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("💡 Dica: Verifique seu token GitHub e conexão com internet")


if __name__ == "__main__":
    main()