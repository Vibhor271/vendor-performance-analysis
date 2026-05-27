import pandas as pd
import os
from sqlalchemy import create_engine
import logging
import time
logging.basicConfig(
    filename="logs/ingestion_db.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)
engine = create_engine('mysql+pymysql://root:@localhost/inventory_db')
def ingest_db(df, table_name, engine):
    '''Ingest the data into database table'''
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists='replace',   # or 'append'
        index=False
    )
def load_raw_data():
    start=time.time()
    path = '.'   # current folder
    
    for file in os.listdir(path):
        if file.endswith('.csv'):
            df = pd.read_csv(os.path.join(path, file))
            
            table_name = file.replace('.csv', '')
            
            logging.info(f"Ingesting {table_name}...")
            ingest_db(df, table_name, engine)
    end=time.time()
    total_time=(end-start)/60
    logging.info('Ingestion complete')
    logging.info(f'\nTotal Time Taken: {total_time} minutes')

if __name__=="__main__":
    load_raw_data()