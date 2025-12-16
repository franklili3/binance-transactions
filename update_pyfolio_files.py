#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于现有交易数据更新pyfolio格式的文件
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def update_positions_and_returns():
    """基于交易数据更新positions和returns文件"""
    
    # 读取交易数据
    try:
        transactions_df = pd.read_csv('transactions_pyfolio.csv', index_col=0, parse_dates=True)
        print(f"读取到 {len(transactions_df)} 条交易记录")
        print(f"交易日期范围: {transactions_df.index.min()} 到 {transactions_df.index.max()}")
    except Exception as e:
        print(f"读取交易文件失败: {e}")
        return
    
    # 获取所有唯一的日期（标准化到日期）
    unique_dates = transactions_df.index.normalize().unique()
    print(f"唯一日期数量: {len(unique_dates)}")
    
    # 计算每日的持仓变化
    daily_positions = []
    daily_returns = []
    
    # 初始假设有10000 USDT的现金
    initial_cash = 10000.0
    current_cash = initial_cash
    current_btc_amount = 0.0
    
    # 按日期处理交易
    for i, date in enumerate(sorted(unique_dates)):
        # 获取当天的交易
        day_transactions = transactions_df[transactions_df.index.normalize() == date]
        
        # 计算当天的交易汇总
        day_volume = day_transactions['txn_volume'].sum()
        day_shares = day_transactions['txn_shares'].sum()
        
        # 假设平均价格（简化处理）
        avg_price = day_volume / day_shares if day_shares != 0 else 0
        
        # 更新持仓（假设买入为正，卖出为负）
        current_btc_amount += day_shares
        current_cash -= day_volume  # 买入减少现金，卖出增加现金
        
        # 计算当前BTC价值（使用估算价格）
        # 简化：假设BTC价格在50000左右，根据交易量调整
        estimated_btc_price = 50000 + (i * 100)  # 简单的价格增长模型
        btc_value = current_btc_amount * estimated_btc_price
        total_value = current_cash + btc_value
        
        # 计算当日收益率
        if i == 0:
            daily_return = 0.0
        else:
            prev_total_value = daily_positions[-1]['total_value'] if daily_positions else initial_cash
            daily_return = (total_value - prev_total_value) / prev_total_value if prev_total_value > 0 else 0.0
        
        # 记录持仓数据
        daily_positions.append({
            'date': date,
            'BTC': btc_value,
            'cash': current_cash,  # 改回cash
            'total_value': total_value
        })
        
        # 记录收益率数据
        daily_returns.append({
            'date': date,
            'return': daily_return
        })
        
        print(f"日期 {date.date()}: BTC数量={current_btc_amount:.6f}, 现金={current_cash:.2f}, 总价值={total_value:.2f}, 收益率={daily_return:.6f}")
    
    # 创建positions DataFrame
    positions_df = pd.DataFrame(daily_positions)
    positions_df.set_index('date', inplace=True)
    positions_df = positions_df[['BTC', 'cash']]  # 只保留BTC和cash列
    
    # 创建returns DataFrame
    returns_df = pd.DataFrame(daily_returns)
    returns_df.set_index('date', inplace=True)
    
    # 保存文件
    positions_df.to_csv('positions_pyfolio.csv')
    returns_df.to_csv('returns_pyfolio.csv')
    
    print(f"\n已更新positions_pyfolio.csv，包含 {len(positions_df)} 行数据")
    print(f"已更新returns_pyfolio.csv，包含 {len(returns_df)} 行数据")
    
    # 显示文件内容
    print("\n=== positions_pyfolio.csv 内容 ===")
    print(positions_df.to_csv())
    
    print("\n=== returns_pyfolio.csv 内容 ===")
    print(returns_df.to_csv())
    
    # 打印摘要
    print("\n=== 数据摘要 ===")
    print(f"初始现金: {initial_cash:.2f} USDT")
    print(f"最终现金: {current_cash:.2f} USDT")
    print(f"最终BTC数量: {current_btc_amount:.6f}")
    print(f"最终总价值: {total_value:.2f} USDT")
    print(f"总收益率: {((total_value - initial_cash) / initial_cash * 100):.2f}%")
    print(f"平均日收益率: {(returns_df['return'].mean() * 100):.4f}%")

if __name__ == "__main__":
    update_positions_and_returns()
