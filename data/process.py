import pandas as pd

def read_df(fname: str) -> pd.DataFrame:
    df = pd.read_csv(fname, sep=';', decimal=',')
    df['ReadTimestamp'] = pd.to_datetime(df['ReadTimestamp'])
    df.sort_values('ReadTimestamp')
    df = df[['Transformer', 'ReadTimestamp', 'Delta A+[kWh]']]
    return df

def main():
    df1 = read_df('Sub71125.csv')
    df2 = read_df('Sub71125_del_1_juni.csv')
    df3 = read_df('Sub71125_16_JUNI_1JULI.csv')
    df4 = read_df('MP71125_1_Juli_31_Juli.csv')

    df = pd.concat([df1, df2, df3, df4])
    df = df.sort_values('ReadTimestamp')
    df = df.drop_duplicates()
    df = df.reset_index(drop=True)
    print(df)

    df.to_csv('out.csv')

if __name__ == '__main__':
    main()
