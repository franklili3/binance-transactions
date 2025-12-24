import pandas as pd
import numpy as np
from datetime import datetime

def analyze_returns_anomalies():
    """分析收益率异常值"""
    print("=== 分析收益率异常值 ===")
    
    # 读取收益率数据
    returns_df = pd.read_csv('returns_pyfolio.csv', index_col=0, parse_dates=True)
    
    # 读取持仓数据
    positions_df = pd.read_csv('positions_pyfolio.csv', index_col=0, parse_dates=True)
    
    # 找出异常值（收益率绝对值大于1）
    anomalies = returns_df[abs(returns_df['return']) > 1].copy()
    print(f"\n发现 {len(anomalies)} 个异常收益率值：")
    for date, row in anomalies.iterrows():
        print(f"{date.date()}: {row['return']:.2%}")
    
    # 分析每个异常日期前后的数据
    print("\n=== 异常日期详细分析 ===")
    for anomaly_date in anomalies.index:
        print(f"\n--- {anomaly_date.date()} ---")
        
        # 获取异常日期前后3天的数据
        start_date = anomaly_date - pd.Timedelta(days=3)
        end_date = anomaly_date + pd.Timedelta(days=3)
        
        # 收益率数据
        returns_window = returns_df.loc[start_date:end_date]
        print("\n收益率窗口：")
        for date, row in returns_window.iterrows():
            if abs(row['return']) > 0.1:  # 只显示绝对值大于10%的
                print(f"  {date.date()}: {row['return']:.2%}")
        
        # 持仓数据
        positions_window = positions_df.loc[start_date:end_date]
        print("\n持仓数据（只显示有变化的资产）：")
        
        # 找出有变化的列
        for col in positions_window.columns:
            if col == 'date':
                continue
            values = positions_window[col]
            if not values.isna().all():  # 如果列中有非空值
                non_null_values = values.dropna()
                if len(non_null_values) > 1:  # 如果有多个非空值
                    changes = non_null_values.diff().dropna()
                    if any(abs(changes) > 0.01):  # 如果有显著变化
                        print(f"  {col}:")
                        for date, value in non_null_values.items():
                            if pd.notna(value):
                                print(f"    {date.date()}: {value:.6f}")

def analyze_positions_calculation():
    """分析持仓计算逻辑"""
    print("\n=== 分析持仓计算逻辑 ===")
    
    # 读取持仓数据
    positions_df = pd.read_csv('positions_pyfolio.csv', index_col=0, parse_dates=True)
    
    print(f"持仓数据形状: {positions_df.shape}")
    print(f"日期范围: {positions_df.index.min()} 到 {positions_df.index.max()}")
    print(f"资产列: {list(positions_df.columns)}")
    
    # 检查每个资产的统计信息
    for asset in positions_df.columns:
        if asset == 'date':
            continue
        values = positions_df[asset].dropna()
        if len(values) > 0:
            print(f"\n{asset} 统计:")
            print(f"  非空值数量: {len(values)}")
            print(f"  最小值: {values.min():.6f}")
            print(f"  最大值: {values.max():.6f}")
            print(f"  平均值: {values.mean():.6f}")
            print(f"  标准差: {values.std():.6f}")
            
            # 检查是否有极端值
            extreme_threshold = values.mean() + 3 * values.std()
            extremes = values[abs(values) > extreme_threshold]
            if len(extremes) > 0:
                print(f"  极端值 (> {extreme_threshold:.6f}):")
                for date, value in extremes.items():
                    print(f"    {date.date()}: {value:.6f}")

def check_portfolio_values():
    """检查投资组合价值计算"""
    print("\n=== 检查投资组合价值 ===")
    
    # 读取持仓数据
    positions_df = pd.read_csv('positions_pyfolio.csv', index_col=0, parse_dates=True)
    
    # 计算每日投资组合总价值
    portfolio_values = positions_df.sum(axis=1)
    
    print(f"投资组合价值统计:")
    print(f"  最小值: {portfolio_values.min():.2f}")
    print(f"  最大值: {portfolio_values.max():.2f}")
    print(f"  平均值: {portfolio_values.mean():.2f}")
    print(f"  标准差: {portfolio_values.std():.2f}")
    
    # 找出价值变化最大的日期
    value_changes = portfolio_values.diff().dropna()
    extreme_changes = value_changes[abs(value_changes) > portfolio_values.mean()]
    
    if len(extreme_changes) > 0:
        print(f"\n极端价值变化日期 (变化 > {portfolio_values.mean():.2f}):")
        for date, change in extreme_changes.items():
            prev_value = portfolio_values.loc[date - pd.Timedelta(days=1)]
            curr_value = portfolio_values.loc[date]
            print(f"  {date.date()}: {prev_value:.2f} -> {curr_value:.2f} (变化: {change:.2f}, {change/prev_value:.2%})")

if __name__ == "__main__":
    analyze_returns_anomalies()
    analyze_positions_calculation()
    check_portfolio_values()
