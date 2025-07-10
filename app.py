# app.py (Dashboard Principal)

import streamlit as st
import pandas as pd
import plotly.express as px
import locale
from datetime import datetime

# --- Configuração da Página e do Locale ---
st.set_page_config(
    page_title="Dashboard Analítico Financeiro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Locale 'pt_BR.UTF-8' não encontrado.")

# --- FUNÇÕES AUXILIARES (do seu código) ---
@st.cache_data
def load_and_clean_data(uploaded_file, sheet_name):
    """Carrega dados do Excel, limpa, converte e CALCULA os valores corretos."""
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=1)
        df.columns = df.columns.str.strip()
        
        currency_cols = ['SUB-TOTAL', 'DESCONTO', 'SERVIÇO']
        for col in currency_cols:
            if col in df.columns:
                df[col] = df[col].apply(clean_money).fillna(0)

        df['A PAGAR'] = df.get('SUB-TOTAL', 0) - df.get('DESCONTO', 0) + df.get('SERVIÇO', 0)
        
        if 'SUB-TOTAL' in df.columns and 'A PAGAR' in df.columns:
            sub_total = df['SUB-TOTAL']
            a_pagar = df['A PAGAR']
            diff = sub_total - a_pagar
            # Trata divisão por zero antes de clipar
            df['PERCENTUAL_DESCONTADO'] = diff.divide(sub_total.where(sub_total != 0, 1), fill_value=0).clip(0, 1).fillna(0)
        else:
            df['PERCENTUAL_DESCONTADO'] = 0.0
        
        if 'DATA' in df.columns:
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
            df.dropna(subset=['DATA'], inplace=True)
            
        text_cols = ['RESPONSÁVEL', 'SETOR', 'DESCRIÇÃO']
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('Não definido')
        return df
    except Exception as e:
        st.error(f"Erro Crítico ao processar o arquivo: {e}")
        return None

def clean_money(value):
    if isinstance(value, (int, float)): return float(value)
    if isinstance(value, str):
        cleaned_value = value.replace('R$', '').strip().replace('.', '').replace(',', '.',)
        return pd.to_numeric(cleaned_value, errors='coerce')
    return 0.0

# --- UI PRINCIPAL ---
st.title("📊 Dashboard Principal")

# --- Sidebar ---
st.sidebar.header("Menu")
uploaded_file = st.sidebar.file_uploader("1. Escolha sua planilha Excel", type=["xlsx", "xls"])

# Inicialização do st.session_state (para compartilhar dados entre páginas)
if 'df_original' not in st.session_state: st.session_state.df_original = None
if 'df_filtered' not in st.session_state: st.session_state.df_filtered = None
if 'selected_sheet' not in st.session_state: st.session_state.selected_sheet = None
if 'date_range' not in st.session_state: st.session_state.date_range = None


if uploaded_file:
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        selected_sheet = st.sidebar.selectbox("2. Selecione a Aba", sheet_names, key="sheet_selector")
        
        df_original = load_and_clean_data(uploaded_file, selected_sheet)
        
        st.session_state.selected_sheet = selected_sheet

        if df_original is not None:
            st.header("🔍 Filtros")
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            df_filtered = df_original.copy()

            with filter_col1:
                if 'SETOR' in df_filtered.columns:
                    setores_options = ["Todos"] + sorted(list(df_filtered['SETOR'].dropna().unique()))
                    selected_setor = st.selectbox("Setor", setores_options)
                    if selected_setor != "Todos": df_filtered = df_filtered[df_filtered['SETOR'] == selected_setor]
                else: st.warning("Coluna 'SETOR' não encontrada.")
            
            with filter_col2:
                if 'RESPONSÁVEL' in df_filtered.columns:
                    responsaveis_options = ["Todos"] + sorted(list(df_filtered['RESPONSÁVEL'].dropna().unique()))
                    selected_responsavel = st.selectbox("Responsável", responsaveis_options)
                    if selected_responsavel != "Todos": df_filtered = df_filtered[df_filtered['RESPONSÁVEL'] == selected_responsavel]
                else: st.warning("Coluna 'RESPONSÁVEL' não encontrada.")
            
            with filter_col3:
                if 'DATA' in df_filtered.columns and not df_filtered['DATA'].empty:
                    min_date, max_date = df_filtered['DATA'].min().date(), df_filtered['DATA'].max().date()
                    selected_date_range = st.date_input("Período", (min_date, max_date), min_value=min_date, max_value=max_date)
                    if len(selected_date_range) == 2:
                        df_filtered = df_filtered[(df_filtered['DATA'].dt.date >= selected_date_range[0]) & (df_filtered['DATA'].dt.date <= selected_date_range[1])]
                        st.session_state.date_range = selected_date_range
                else: st.warning("Coluna 'DATA' não encontrada ou vazia.")
            
            st.session_state.df_filtered = df_filtered
            
            st.markdown("---")
            st.header("Visão Geral do Período Selecionado")
            total_a_pagar = df_filtered['A PAGAR'].sum()
            total_desconto = df_filtered['DESCONTO'].sum()
            
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(label="Total a Pagar", value=locale.currency(total_a_pagar, grouping=True))
            kpi2.metric(label="Total de Descontos", value=locale.currency(total_desconto, grouping=True))
            kpi3.metric(label="Nº de Lançamentos", value=f"{len(df_filtered)}")
            
            st.markdown("---")
            
            st.header("Principais Análises de Desconto")
            maior_desconto_linha = df_filtered.nlargest(1, 'DESCONTO')
            
            analysis1, analysis2 = st.columns(2)
            with analysis1:
                st.info("**Maior Desconto Individual**")
                if 'RESPONSÁVEL' in maior_desconto_linha.columns and not maior_desconto_linha.empty:
                    st.markdown(f"#### {locale.currency(maior_desconto_linha['DESCONTO'].values[0], grouping=True)}")
                    st.markdown(f"**Responsável:** {maior_desconto_linha['RESPONSÁVEL'].values[0]}")
                    st.markdown(f"**Descrição:** `{maior_desconto_linha['DESCRIÇÃO'].values[0]}`")

            with analysis2:
                st.warning("**Responsável com Maior Soma de Descontos**")
                if 'RESPONSÁVEL' in df_filtered.columns:
                    resp_soma_desconto = df_filtered.groupby('RESPONSÁVEL')['DESCONTO'].sum().nlargest(1)
                    if not resp_soma_desconto.empty:
                        st.markdown(f"#### {resp_soma_desconto.index[0]}")
                        st.markdown(f"Total de Descontos: **{locale.currency(resp_soma_desconto.values[0], grouping=True)}**")
            
            st.markdown("---")
            
# --- NOVA SEÇÃO: ANÁLISE DE POLÍTICAS DE DESCONTO (Versão 3 - CORRIGIDA) ---
            st.header("🕵️ Análise de Políticas de Desconto")
            st.caption("Análise de lançamentos fora das políticas de desconto padrão. As categorias são mutuamente exclusivas.")

            # Pré-requisito: Verificar se as colunas necessárias existem
            if 'PERCENTUAL_DESCONTADO' in df_filtered.columns and 'SETOR' in df_filtered.columns:
                
                df_analise = df_filtered.copy()
                # A normalização para minúsculas continua importante
                df_analise['SETOR_NORMALIZADO'] = df_analise['SETOR'].str.strip().str.lower()

                # --- CORREÇÃO: Lógica de filtragem mais robusta e com exclusividade garantida ---

                # 1. Identifica 'Funcionário' (>10%) primeiro
                # Usa .str.contains() para ignorar acentos e ser mais flexível.
                idx_func = df_analise[
                    (df_analise['SETOR_NORMALIZADO'].str.contains('funcion', case=False, na=False)) & 
                    (df_analise['PERCENTUAL_DESCONTADO'] > 0.10)
                ].index
                descontos_funcionario_fora_politica = df_analise.loc[idx_func]
                
                # 2. Em seguida, identifica 'Cortesia' (>5%) dos dados restantes
                df_sem_func = df_analise.drop(idx_func) # Remove os que já foram classificados
                idx_cort = df_sem_func[
                    (df_sem_func['SETOR_NORMALIZADO'].str.contains('cortesia', case=False, na=False)) &
                    (df_sem_func['PERCENTUAL_DESCONTADO'] > 0.05)
                ].index
                descontos_cortesia_fora_politica = df_analise.loc[idx_cort]

                # 3. Por fim, analisa 'Outros de Alto Valor' (80-99%) do que sobrou
                df_restante = df_analise.drop(idx_func).drop(idx_cort) # Remove ambos os grupos já classificados
                descontos_alto_valor = df_restante[
                    (df_restante['PERCENTUAL_DESCONTADO'] >= 0.80) & 
                    (df_restante['PERCENTUAL_DESCONTADO'] <= 0.99)
                ]
                
                # --- Recontagem com os DataFrames corretos ---
                count_funcionario_fora_politica = len(descontos_funcionario_fora_politica)
                count_cortesia_fora_politica = len(descontos_cortesia_fora_politica)
                count_alto_valor = len(descontos_alto_valor)

                # --- Exibição dos Contadores em Colunas ---
                policy1, policy2, policy3 = st.columns(3)

                with policy1:
                    st.error("**Política de Funcionários**")
                    st.metric(label="Descontos > 10%", value=f"{count_funcionario_fora_politica}")
                    if count_funcionario_fora_politica > 0:
                        with st.expander("Ver detalhes e justificativas"):
                            df_display = descontos_funcionario_fora_politica[['DATA', 'RESPONSÁVEL', 'DESCRIÇÃO', 'PERCENTUAL_DESCONTADO']].copy()
                            df_display['PERCENTUAL_DESCONTADO'] = df_display['PERCENTUAL_DESCONTADO'].map('{:.2%}'.format)
                            st.dataframe(df_display, use_container_width=True)

                with policy2:
                    st.warning("**Política de Cortesias**")
                    st.metric(label="Descontos > 5%", value=f"{count_cortesia_fora_politica}")
                    if count_cortesia_fora_politica > 0:
                        with st.expander("Ver detalhes e justificativas"):
                            df_display = descontos_cortesia_fora_politica[['DATA', 'RESPONSÁVEL', 'DESCRIÇÃO', 'PERCENTUAL_DESCONTADO']].copy()
                            df_display['PERCENTUAL_DESCONTADO'] = df_display['PERCENTUAL_DESCONTADO'].map('{:.2%}'.format)
                            st.dataframe(df_display, use_container_width=True)
                
                with policy3:
                    st.info("**Outros Descontos de Alto Valor**")
                    st.metric(label="Lançamentos entre 80% e 99%", value=f"{count_alto_valor}")
                    if count_alto_valor > 0:
                        with st.expander("Ver lançamentos"):
                            df_display = descontos_alto_valor[['DATA', 'RESPONSÁVEL', 'DESCRIÇÃO', 'PERCENTUAL_DESCONTADO']].copy()
                            df_display['PERCENTUAL_DESCONTADO'] = df_display['PERCENTUAL_DESCONTADO'].map('{:.2%}'.format)
                            st.dataframe(df_display, use_container_width=True)

                st.markdown("---") 

                st.subheader("🏆 Destaques por Categoria de Desconto")
                kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

                with kpi_col1:
                    st.error("**Destaques: Funcionário (>10%)**")
                    if not descontos_funcionario_fora_politica.empty:
                        soma_desconto_func = descontos_funcionario_fora_politica.groupby('RESPONSÁVEL')['DESCONTO'].sum().nlargest(1)
                        if not soma_desconto_func.empty:
                            st.markdown(f"**Maior Somatório:** {soma_desconto_func.index[0]} ({locale.currency(soma_desconto_func.values[0], grouping=True)})")
                        
                        maior_desc_perc_func = descontos_funcionario_fora_politica.nlargest(1, 'PERCENTUAL_DESCONTADO')
                        if not maior_desc_perc_func.empty:
                            st.markdown(f"**Maior % Individual:** {maior_desc_perc_func['PERCENTUAL_DESCONTADO'].values[0]:.2%} (Resp: {maior_desc_perc_func['RESPONSÁVEL'].values[0]})")
                    else:
                        st.markdown("_Nenhum lançamento nesta categoria._")

                with kpi_col2:
                    st.warning("**Destaques: Cortesia (>5%)**")
                    if not descontos_cortesia_fora_politica.empty:
                        soma_desconto_cort = descontos_cortesia_fora_politica.groupby('RESPONSÁVEL')['DESCONTO'].sum().nlargest(1)
                        if not soma_desconto_cort.empty:
                             st.markdown(f"**Maior Somatório:** {soma_desconto_cort.index[0]} ({locale.currency(soma_desconto_cort.values[0], grouping=True)})")

                        maior_desc_perc_cort = descontos_cortesia_fora_politica.nlargest(1, 'PERCENTUAL_DESCONTADO')
                        if not maior_desc_perc_cort.empty:
                            st.markdown(f"**Maior % Individual:** {maior_desc_perc_cort['PERCENTUAL_DESCONTADO'].values[0]:.2%} (Resp: {maior_desc_perc_cort['RESPONSÁVEL'].values[0]})")
                    else:
                        st.markdown("_Nenhum lançamento nesta categoria._")
                
                with kpi_col3:
                    st.info("**Destaques: Outros (80%-99%)**")
                    if not descontos_alto_valor.empty:
                        soma_desconto_alto = descontos_alto_valor.groupby('RESPONSÁVEL')['DESCONTO'].sum().nlargest(1)
                        if not soma_desconto_alto.empty:
                            st.markdown(f"**Maior Somatório:** {soma_desconto_alto.index[0]} ({locale.currency(soma_desconto_alto.values[0], grouping=True)})")
                    else:
                        st.markdown("_Nenhum lançamento nesta categoria._")

            else:
                st.warning("Colunas 'SETOR' ou 'PERCENTUAL_DESCONTADO' não encontradas para a análise de políticas.")
            
            st.markdown("---")
            
            st.header("Visualizações Gráficas")
            graph_col1, graph_col2 = st.columns(2)
            
            with graph_col1:
                if 'RESPONSÁVEL' in df_filtered.columns and 'DESCONTO' in df_filtered.columns:
                    total_desconto_resp = df_filtered.groupby('RESPONSÁVEL')['DESCONTO'].sum().sort_values(ascending=False).reset_index()
                    fig1 = px.bar(total_desconto_resp, x='RESPONSÁVEL', y='DESCONTO', title="Soma de Descontos por Responsável", text='DESCONTO')
                    fig1.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
                    st.plotly_chart(fig1, use_container_width=True)
            
            with graph_col2:
                if 'SETOR' in df_filtered.columns and 'SUB-TOTAL' in df_filtered.columns:
                    total_subtotal_setor = df_filtered.groupby('SETOR')['SUB-TOTAL'].sum().reset_index()
                    fig2 = px.pie(total_subtotal_setor, values='SUB-TOTAL', names='SETOR', title="Distribuição do Sub-Total por Setor", hole=.4)
                    fig2.update_traces(textinfo='percent+label', texttemplate='%{percent:.2%}')
                    st.plotly_chart(fig2, use_container_width=True)
                
            st.markdown("---")
            
            st.header("Dados Filtrados Detalhados")
            colunas_existentes_principais = ['DATA', 'SETOR', 'RESPONSÁVEL', 'DESCRIÇÃO', 'SUB-TOTAL', 'DESCONTO', 'SERVIÇO', 'A PAGAR', 'PERCENTUAL_DESCONTADO']
            colunas_existentes_para_exibir = [col for col in colunas_existentes_principais if col in df_filtered.columns]
            
            # --- INÍCIO DA CORREÇÃO ---
            # 1. Criamos uma cópia do DataFrame apenas para a exibição na tabela.
            # Isso garante que os dados originais (com percentual de 0 a 1) permaneçam intactos.
            df_para_exibir = df_filtered.copy()

            # 2. Verificamos se a coluna existe e multiplicamos por 100.
            if 'PERCENTUAL_DESCONTADO' in df_para_exibir.columns:
                df_para_exibir['PERCENTUAL_DESCONTADO'] = df_para_exibir['PERCENTUAL_DESCONTADO'] * 100

            # 3. Definimos a configuração da coluna.
            column_configs = {
                "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "SUB-TOTAL": st.column_config.NumberColumn("Sub-Total", format="R$ %.2f"),
                "DESCONTO": st.column_config.NumberColumn("Desconto", format="R$ %.2f"),
                "SERVIÇO": st.column_config.NumberColumn("Serviço", format="R$ %.2f"),
                "A PAGAR": st.column_config.NumberColumn("A Pagar (Calculado)", format="R$ %.2f"),
                # Agora que o valor é 99.0 (e não 0.99), esta formatação funcionará.
                # Ela irá formatar para "99.00" e adicionar o "%" no final.
                "PERCENTUAL_DESCONTADO": st.column_config.NumberColumn("% Descontado", format="%.2f%%")
            }
            
            # 4. Usamos o novo DataFrame 'df_para_exibir' para a visualização.
            st.dataframe(df_para_exibir[colunas_existentes_para_exibir], column_config=column_configs, use_container_width=True)
            # --- FIM DA CORREÇÃO ---

    except Exception as e:
        st.sidebar.error(f"Não foi possível processar a planilha. Verifique o formato do arquivo.")
        st.session_state.df_original = None
        
else:
    st.info("⬆️ Para começar, carregue um arquivo Excel e selecione uma aba na sidebar.")