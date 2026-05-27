import os
import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# ================= CREATE LOGS FOLDER ================= #

os.makedirs("logs", exist_ok=True)

# ================= LOGGING CONFIGURATION ================= #

logging.basicConfig(
    filename='logs/get_vendor_summary.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

# ================= MYSQL CONNECTION ================= #

engine = create_engine(
    "mysql+pymysql://root:@localhost/inventory",
    pool_pre_ping=True,
    pool_recycle=3600
)

# ================= CLEANING FUNCTION ================= #

def clean_data(df):

    logging.info("Data cleaning started")

    # Convert datatype
    df['Volume'] = pd.to_numeric(
        df['Volume'],
        errors='coerce'
    )

    # Fill missing values
    df.fillna(0, inplace=True)

    # Remove spaces
    df['VendorName'] = (
        df['VendorName']
        .astype(str)
        .str.strip()
    )

    df['Description'] = (
        df['Description']
        .astype(str)
        .str.strip()
    )

    # ================= KPI CREATION ================= #

    # Gross Profit
    df['GrossProfit'] = (
        df['TotalSalesDollars']
        - df['TotalPurchaseDollars']
    )

    # Profit Margin
    df['ProfitMargin'] = np.where(
        df['TotalSalesDollars'] != 0,

        (
            df['GrossProfit']
            / df['TotalSalesDollars']
        ) * 100,

        0
    )

    # Stock Turnover
    df['StockTurnover'] = np.where(
        df['TotalPurchaseQuantity'] != 0,

        df['TotalSalesQuantity']
        / df['TotalPurchaseQuantity'],

        0
    )

    # Sales To Purchase Ratio
    df['SalesToPurchaseRatio'] = np.where(
        df['TotalPurchaseDollars'] != 0,

        df['TotalSalesDollars']
        / df['TotalPurchaseDollars'],

        0
    )

    # Remove inf values
    df.replace(
        [np.inf, -np.inf],
        0,
        inplace=True
    )

    df.fillna(0, inplace=True)

    logging.info("Data cleaning completed")

    return df


# ================= MAIN FUNCTION ================= #

def create_vendor_summary():

    logging.info("Vendor summary creation started")

    query = """

    WITH FreightSummary AS (

        SELECT
            VendorNumber,
            SUM(Freight) AS FreightCost

        FROM vendor_invoice

        GROUP BY VendorNumber
    ),

    PurchaseSummary AS (

        SELECT

            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,

            pp.Price AS ActualPrice,
            pp.Volume,

            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars

        FROM purchases p

        JOIN purchase_prices pp
            ON p.Brand = pp.Brand

        WHERE p.PurchasePrice > 0

        GROUP BY

            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Price,
            pp.Volume
    ),

    SalesSummary AS (

        SELECT

            VendorNo,
            Brand,

            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(ExciseTax) AS TotalExciseTax

        FROM sales

        GROUP BY VendorNo, Brand
    )

    SELECT

        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,

        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,

        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,

        fs.FreightCost

    FROM PurchaseSummary ps

    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand

    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber

    ORDER BY ps.TotalPurchaseDollars DESC

    """

    # ================= FETCH DATA ================= #

    vendor_sales_summary = pd.read_sql_query(
        query,
        engine
    )

    logging.info("SQL query executed successfully")

    # ================= CLEAN DATA ================= #

    vendor_sales_summary = clean_data(
        vendor_sales_summary
    )

    # ================= STORE INTO MYSQL ================= #

    vendor_sales_summary.to_sql(
        name='vendor_sales_summary',
        con=engine,
        if_exists='replace',
        index=False,
        method='multi',
        chunksize=1000
    )

    logging.info("vendor_sales_summary table created successfully")

    return vendor_sales_summary


# ================= RUN FUNCTION ================= #

vendor_sales_summary = create_vendor_summary()

# ================= PREVIEW DATA ================= #

print(vendor_sales_summary.head())