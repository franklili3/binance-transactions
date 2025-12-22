#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新后的收益率计算功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from binance_transactions import BinanceTransactions

def test_price_fallback():
    """测试备用价格获取方法"""
    print("=== 测试比特币价格下载功能 ===")
    
    try:
        # 创建一个临时实例来测试价格获取
        # 使用模拟的API密钥来避免实际连接
        os.environ['BINANCE_API_KEY'] = 'test_key'
        os.environ['BINANCE_SECRET_KEY'] = 'test_secret'
        
        analyzer = BinanceTransactions()
        
        # 测试获取比特币价格数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        btc_price_df = analyzer.get_bitcoin_price_data(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if not btc_price_df.empty:
            print(f"✓ 成功获取 {len(btc_price_df)} 天的比特币价格数据")
            print(f"  日期范围: {btc_price_df.index.min()} 到 {btc_price_df.index.max()}")
            print(f"  价格范围: {btc_price_df['close'].min():.2f} - {btc_price_df['close'].max():.2f} USDT")
            print(f"  数据列: {list(btc_price_df.columns)}")
            return True
        else:
            print("✗ 获取比特币价格数据失败")
            return False
            
    except Exception as e:
        print(f"✗ 测试价格获取失败: {e}")
        return False
    finally:
        # 清理环境变量
        os.environ.pop('BINANCE_API_KEY', None)
        os.environ.pop('BINANCE_SECRET_KEY', None)

def test_portfolio_based_returns():
    """测试基于仓位和价格的收益率计算"""
    print("\n=== 测试基于仓位和价格的收益率计算 ===")
    
    try:
        # 创建模拟交易数据
        np.random.seed(42)
        
        # 创建模拟交易记录
        transactions_data = []
        base_date = datetime.now() - timedelta(days=7)
        
        # 生成2笔模拟交易
        for i in range(2):
            tx_date = base_date + timedelta(days=i*2)
            
            if i == 0:
                # 第一笔交易：买入BTC
                transactions_data.append({
                    'date': tx_date,
                    'txn_volume': 1000.0,  # 花费1000 USDT
                    'txn_shares': 0.01     # 买入0.01 BTC
                })
            else:
                # 第二笔交易：卖出部分BTC
                transactions_data.append({
                    'date': tx_date,
                    'txn_volume': -600.0,  # 收入600 USDT
                    'txn_shares': -0.006    # 卖出0.006 BTC
                })
        
        transactions_df = pd.DataFrame(transactions_data)
        transactions_df.set_index('date', inplace=True)
        
        print(f"创建模拟交易数据: {len(transactions_df)} 笔交易")
        print(transactions_df)
        
        # 创建模拟的原始交易数据（用于calculate_returns方法）
        mock_raw_transactions = [
            {
                'datetime': (base_date + timedelta(days=0)).isoformat(),
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'amount': 0.01,
                'cost': 1000.0,
                'price': 100000.0
            },
            {
                'datetime': (base_date + timedelta(days=2)).isoformat(),
                'symbol': 'BTC/USDT',
                'side': 'sell',
                'amount': 0.006,
                'cost': 600.0,
                'price': 100000.0
            }
        ]
        
        # 创建模拟的比特币价格数据
        price_data = []
        for i in range(7):
            date = base_date + timedelta(days=i)
            price = 100000.0 + np.random.normal(0, 1000)  # 价格波动
            
            price_data.append({
                'datetime': date,
                'open': price,
                'high': price * 1.02,
                'low': price * 0.98,
                'close': price,
                'volume': 1000
            })
        
        btc_price_df = pd.DataFrame(price_data)
        btc_price_df.set_index('datetime', inplace=True)
        
        # 创建分析器实例
        os.environ['BINANCE_API_KEY'] = 'test_key'
        os.environ['BINANCE_SECRET_KEY'] = 'test_secret'
        
        analyzer = BinanceTransactions()
        
        # 测试每日持仓计算
        daily_positions = analyzer._calculate_daily_positions(mock_raw_transactions, btc_price_df)
        print(f"✓ 计算每日持仓: {len(daily_positions)} 天")
        print(f"  持仓列: {list(daily_positions.columns)}")
        
        # 测试投资组合价值计算
        daily_portfolio_value = analyzer._calculate_portfolio_value(daily_positions, btc_price_df)
        print(f"✓ 计算投资组合价值: {len(daily_portfolio_value)} 天")
        print(f"  价值范围: {daily_portfolio_value.min():.2f} - {daily_portfolio_value.max():.2f} USDT")
        
        # 测试收益率计算
        returns = daily_portfolio_value.pct_change().fillna(0)
        print(f"✓ 计算收益率: {len(returns)} 天")
        print(f"  收益率范围: {returns.min():.4f} - {returns.max():.4f}")
        
        # 测试完整的calculate_returns方法（修复参数问题）
        returns_series = analyzer.calculate_returns(transactions_df)
        print(f"✓ 完整收益率计算: {len(returns_series)} 天")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试收益率计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理环境变量
        os.environ.pop('BINANCE_API_KEY', None)
        os.environ.pop('BINANCE_SECRET_KEY', None)

def test_fallback_method():
    """测试备用方法获取价格数据"""
    print("\n=== 测试备用方法获取价格数据 ===")
    
    try:
        # 创建分析器实例
        os.environ['BINANCE_API_KEY'] = 'test_key'
        os.environ['BINANCE_SECRET_KEY'] = 'test_secret'
        
        analyzer = BinanceTransactions()
        
        # 测试备用方法
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        btc_price_df = analyzer._get_bitcoin_price_fallback(
            start_date=start_date,
            end_date=end_date,
            days=5
        )
        
        if not btc_price_df.empty:
            print(f"✓ 备用方法成功获取 {len(btc_price_df)} 天的比特币价格数据")
            print(f"  日期范围: {btc_price_df.index.min()} 到 {btc_price_df.index.max()}")
            print(f"  价格范围: {btc_price_df['close'].min():.2f} - {btc_price_df['close'].max():.2f} USDT")
            return True
        else:
            print("✗ 备用方法获取比特币价格数据失败")
            return False
            
    except Exception as e:
        print(f"✗ 备用方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理环境变量
        os.environ.pop('BINANCE_API_KEY', None)
        os.environ.pop('BINANCE_SECRET_KEY', None)

def main():
    """主函数"""
    print("开始测试更新后的收益率计算功能...\n")
    
    # 运行各项测试
    tests = [
        ("比特币价格下载", test_price_fallback),
        ("收益率计算", test_portfolio_based_returns),
        ("备用方法", test_fallback_method)
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    # 打印测试结果摘要
    print("\n" + "="*50)
    print("测试结果摘要:")
    print("="*50)
    
    passed_count = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed_count += 1
    
    print(f"\n总计: {passed_count}/{len(results)} 测试通过")
    
    if passed_count == len(results):
        print("🎉 所有测试通过！")
        return True
    else:
        print("⚠️  有测试失败，请检查代码")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
