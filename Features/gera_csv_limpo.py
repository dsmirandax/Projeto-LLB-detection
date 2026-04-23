import pandas as pd
import csv

input_file = "features_malicious.csv"

# Detecta separador automaticamente
with open(input_file, "r", encoding="utf-8") as f:
    sample = f.read(4096)
    dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
    sep = dialect.delimiter

# Lê o CSV
df = pd.read_csv(input_file, sep=sep)

# Remove colunas longas/menos úteis para visualização
drop_cols = ["il_like_sequence", "file_path"]
df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

# Garante que existe file_name
if "file_name" not in df.columns:
    raise ValueError("A coluna 'file_name' não foi encontrada no CSV.")

# Coloca file_name como índice e transpõe
df_t = df.set_index("file_name").T.reset_index()
df_t = df_t.rename(columns={"index": "feature"})

# Salva em CSV e Excel
df_t.to_csv("dataset_malicious.csv", index=False, encoding="utf-8-sig")
df_t.to_excel("dataset_malicious.xlsx", index=False)

print("Arquivos gerados:")
print("- dataset_malicious.csv")
print("- dataset_malicious.xlsx")
print("\nPrévia:")
print(df_t.head(15))