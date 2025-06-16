# Sistema EAN para Windows 11

Sistema de cadastro de produtos por código EAN adaptado para execução local no Windows 11.

## Características

- ✅ Interface web moderna e responsiva
- ✅ Banco de dados SQLite (sem necessidade de configuração)
- ✅ Busca automática de produtos por EAN
- ✅ Sistema de usuários com níveis de acesso
- ✅ Exportação para Excel
- ✅ Painel administrativo completo
- ✅ Instalação automatizada para Windows

## Requisitos do Sistema

- Windows 11 (versão 21H2 ou superior)
- Python 3.8 ou superior
- 4GB RAM (recomendado 8GB)
- 2GB espaço livre em disco
- Conexão com internet (para busca de produtos)

## Instalação

1. **Baixe e extraia** o sistema em uma pasta de sua escolha
2. **Execute como administrador**: `instalar.bat`
3. **Aguarde** a instalação das dependências

## Como Usar

1. **Execute**: `iniciar_sistema.bat`
2. **Acesse**: http://localhost:5000 no seu navegador
3. **Login administrativo**:
   - Usuário: `admin`
   - Senha: `admin`

## Funcionalidades Principais

### Cadastro de Produtos
- Digite o código EAN para busca automática
- Preenchimento automático de informações
- Soma automática de quantidades para produtos repetidos
- Validação de dados

### Sistema de Usuários
- Cadastro de novos usuários
- Login seguro com hash de senhas
- Níveis de acesso (usuário/administrador)

### Painel Administrativo
- Estatísticas do sistema
- Gestão de usuários
- Exportação de relatórios
- Visualização de atividades

### Exportação
- Formato Excel (.xlsx)
- Campos: EAN, Descrição, Cor, Voltagem, Modelo, Quantidade
- Download direto pelo navegador

## Estrutura do Projeto

```
ean_system/
├── src/
│   ├── models/          # Modelos de dados
│   ├── templates/       # Templates HTML
│   ├── static/          # Arquivos estáticos
│   ├── database/        # Banco de dados SQLite
│   ├── exports/         # Arquivos exportados
│   └── main.py          # Aplicação principal
├── venv/                # Ambiente virtual Python
├── instalar.bat         # Script de instalação
├── iniciar_sistema.bat  # Script de inicialização
└── requirements.txt     # Dependências Python
```

## Tecnologias Utilizadas

- **Flask 3.1.0** - Framework web
- **SQLAlchemy 2.0.40** - ORM para banco de dados
- **SQLite** - Banco de dados local
- **Bootstrap 5** - Interface responsiva
- **Pandas** - Manipulação de dados
- **OpenPyXL** - Exportação Excel

## Diferenças da Versão Original

### Adaptações para Windows 11

1. **Banco de Dados**: SQLite ao invés de PostgreSQL
2. **Instalação**: Scripts .bat para automação
3. **Dependências**: Removidas dependências específicas do Linux
4. **Interface**: Otimizada para uso local
5. **Configuração**: Simplificada para ambiente desktop

### Melhorias Implementadas

- Interface mais moderna com Bootstrap 5
- Scripts de instalação automatizada
- Melhor tratamento de erros
- Documentação completa em português
- Responsividade aprimorada

## Solução de Problemas

### Python não encontrado
- Instale Python 3.8+ de https://python.org
- Marque "Add Python to PATH" durante instalação

### Erro de permissões
- Execute os scripts como administrador
- Clique com botão direito → "Executar como administrador"

### Porta 5000 ocupada
- Feche outros programas que usam a porta 5000
- Ou edite `src/main.py` para usar outra porta

### Antivírus bloqueando
- Adicione a pasta do sistema às exceções do antivírus
- Temporariamente desabilite proteção em tempo real

## Suporte

Para suporte técnico ou dúvidas:
- Consulte a documentação completa
- Verifique os logs de erro no terminal
- Certifique-se que todos os requisitos estão atendidos

## Licença

Sistema desenvolvido para uso interno. Todos os direitos reservados.

---

**Versão**: 1.0  
**Data**: Junho 2025  
**Compatibilidade**: Windows 11

