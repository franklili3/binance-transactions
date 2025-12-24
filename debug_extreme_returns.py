import pandas as pd
import numpy as np

# 读取数据文件
print("=== 调试极端收益率值 ===\n")

# 读取收益率数据
returns_df = pd.read_csv('returns_pyfolio.csv', index_col=0, parse_dates=True)
returns_df.index.name = 'date'

# 读取持仓数据
positions_df = pd.read_csv('positions_pyfolio.csv', index_col=0, parse_dates=True)
positions_df.index.name = 'date'

# 读取交易数据
transactions_df = pd.read_csv('transactions_pyfolio.csv', parse_dates=['date'])

print(f"收益率数据范围: {returns_df.index.min()} 到 {returns_df.index.max()}")
print(f"持仓数据范围: {positions_df.index.min()} 到 {positions_df.index.max()}\n")

# 找出极端收益率值
extreme_threshold = 10  # 超过1000%的收益率
extreme_returns = returns_df[abs(returns_df['return']) > extreme_threshold].copy()

print(f"=== 发现 {len(extreme_returns)} 个极端收益率值（绝对值 > {extreme_threshold}） ===\n")

for date, row in extreme_returns.iterrows():
    print(f"日期: {date.strftime('%Y-%m-%d')}")
    print(f"  收益率: {row['return']:.6f} ({row['return']*100:.2f}%)")
    
    # 获取前一天的日期
    prev_date = date - pd.Timedelta(days=1)
    
    # 检查持仓数据
    if date in positions_df.index:
        current_portfolio = positions_df.loc[date, 'cash'] + positions_df.loc[date, 'BTC']
        print(f"  当日组合价值: {current_portfolio:.2f}")
        print(f"    现金: {positions_df.loc[date, 'cash']:.2f}")
        print(f"    BTC价值: {positions_df.loc[date, 'BTC']:.2f}")
        
        # BTC数量无法计算，因为缺少价格数据
        print(f"    BTC数量: 无法计算（缺少价格数据）")
    
    if prev_date in positions_df.index:
        prev_portfolio = positions_df.loc[prev_date, 'cash'] + positions_df.loc[prev_date, 'BTC']
        print(f"  前日组合价值: {prev_portfolio:.2f}")
        print(f"    现金: {positions_df.loc[prev_date, 'cash']:.2f}")
        print(f"    BTC价值: {positions_df.loc[prev_date, 'BTC']:.2f}")
        
        # BTC数量无法计算，因为缺少价格数据
        print(f"    BTC数量: 无法计算（缺少价格数据）")
    
    # 手动计算收益率验证
    if prev_date in positions_df.index and date in positions_df.index:
        prev_total = positions_df.loc[prev_date, 'cash'] + positions_df.loc[prev_date, 'BTC']
        current_total = positions_df.loc[date, 'cash'] + positions_df.loc[date, 'BTC']
        
        if prev_total > 0:
            calculated_return = (current_total - prev_total) / prev_total
            print(f"  手动计算收益率: {calculated_return:.6f} ({calculated_return*100:.2f}%)")
            print(f"  与记录的差异: {abs(calculated_return - row['return']):.6f}")
    
    # 检查当天的交易
    day_transactions = transactions_df[transactions_df['date'].dt.date == date.date()]
    if len(day_transactions) > 0:
        print(f"  当日交易数量: {len(day_transactions)}")
        for _, trans in day_transactions.iterrows():
            print(f"    {trans['symbol']} {trans['side']}: {trans['amount']:.6f} @ {trans['price']:.2f}")
    
    print()

# 检查收益率分布
print("=== 收益率统计 ===")
print(f"收益率范围: {returns_df['return'].min():.6f} 到 {returns_df['return'].max():.6f}")
print(f"超过1000%的数量: {len(returns_df[abs(returns_df['return']) > 10])}")
print(f"超过100%的数量: {len(returns_df[abs(returns_df['return']) > 1])}")
print(f"超过50%的数量: {len(returns_df[abs(returns_df['return']) > 0.5])}")
print(f"正常范围(-50%到50%)的数量: {len(returns_df[abs(returns_df['return']) <= 0.5])}")

# 检查持仓价值的变化
print("\n=== 持仓价值变化分析 ===")
portfolio_values = positions_df['cash'] + positions_df['BTC']
portfolio_changes = portfolio_values.pct_change().dropna()

extreme_portfolio_changes = portfolio_changes[abs(portfolio_changes) > 10]
print(f"持仓价值极端变化数量: {len(extreme_portfolio_changes)}")

for date, change in extreme_portfolio_changes.items():
    print(f"日期: {date.strftime('%Y-%m-%d')}, 变化: {change:.6f} ({change*100:.2f}%)")
    prev_val = portfolio_values.loc[date - pd.Timedelta(days=1)]
    curr_val = portfolio_values.loc[date]
    print(f"  前日价值: {prev_val:.2f}, 当日价值: {curr_val:.2f}")

# 检查可能的除零或无穷大问题
print("\n=== 数据完整性检查 ===")
print(f"持仓数据中的NaN数量: {positions_df.isnull().sum().sum()}")
print(f"持仓数据中的无穷大数量: {np.isinf(positions_df).sum().sum()}")
print(f"收益率数据中的NaN数量: {returns_df.isnull().sum().sum()}")
print(f"收益率数据中的无穷大数量: {np.isinf(returns_df).sum().sum()}")

# 检查是否有零价值的持仓导致除零
zero_portfolios = portfolio_values[portfolio_values == 0]
print(f"零价值持仓的数量: {len(zero_portfolios)}")
if len(zero_portfolios) > 0:
    print("零价值持仓日期:")
    for date in zero_portfolios.index:
        print(f"  {date.strftime('%Y-%m-%d')}")
