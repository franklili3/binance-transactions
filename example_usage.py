#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用示例：演示如何使用binance_copy_trade_transactions.py
包含测试交易检查、API权限验证、模拟交易生成等功能
"""

from binance_transactions import BinanceTransactions
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_api_permissions(analyzer):
    """
    检查API密钥权限
    
    Args:
        analyzer: BinanceTransactions实例
        
    Returns:
        dict: 权限检查结果
    """
    print("=== 检查API密钥权限 ===")
    
    permissions = {
        'can_read_balance': False,
        'can_read_trades': False,
        'can_read_orders': False,
        'can_read_positions': False,
        'can_trade': False
    }
    
    try:
        # 检查读取余额权限
        balance = analyzer.exchange.fetch_balance()
        permissions['can_read_balance'] = True
        print("✓ 余额读取权限正常")
    except Exception as e:
        print(f"✗ 余额读取权限失败: {e}")
    
    try:
        # 检查读取交易记录权限
        trades = analyzer.exchange.fetch_my_trades(symbol='BTC/USDT', limit=1)
        permissions['can_read_trades'] = True
        print("✓ 交易记录读取权限正常")
    except Exception as e:
        print(f"✗ 交易记录读取权限失败: {e}")
    
    try:
        # 检查读取订单权限
        orders = analyzer.exchange.fetch_orders(symbol='BTC/USDT', limit=1)
        permissions['can_read_orders'] = True
        print("✓ 订单读取权限正常")
    except Exception as e:
        print(f"✗ 订单读取权限失败: {e}")
    
    try:
        # 检查读取持仓权限
        positions = analyzer.exchange.fetch_positions()
        permissions['can_read_positions'] = True
        print("✓ 持仓读取权限正常")
    except Exception as e:
        print(f"✗ 持仓读取权限失败: {e}")
    
    try:
        # 检查交易权限（通过创建小额测试订单）
        if hasattr(analyzer.exchange, 'sandbox') and analyzer.exchange.sandbox:
            # 在测试网中尝试创建订单
            test_order = analyzer.exchange.create_market_buy_order('BTC/USDT', 0.001)
            # 立即取消以避免实际交易
            analyzer.exchange.cancel_order(test_order['id'], 'BTC/USDT')
            permissions['can_trade'] = True
            print("✓ 交易权限正常（测试网验证）")
        else:
            print("⚠ 生产环境跳过交易权限检查")
    except Exception as e:
        print(f"✗ 交易权限失败: {e}")
    
    return permissions

def check_test_transactions(analyzer, days=7):
    """
    检查账户是否有测试交易
    
    Args:
        analyzer: BinanceTransactions实例
        days: 检查天数
        
    Returns:
        bool: 是否有测试交易
        list: 交易记录
    """
    print(f"\n=== 检查最近{days}天的测试交易 ===")
    
    try:
        # 获取主要交易对的交易记录
        major_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        all_transactions = []
        
        for symbol in major_symbols:
            try:
                transactions = analyzer.get_all_transactions(symbol=symbol, days=days)
                if transactions:
                    all_transactions.extend(transactions)
                    print(f"✓ {symbol}: 找到 {len(transactions)} 条交易记录")
                else:
                    print(f"- {symbol}: 无交易记录")
            except Exception as e:
                print(f"✗ {symbol}: 获取失败 - {e}")
        
        if all_transactions:
            print(f"\n✓ 总共找到 {len(all_transactions)} 条测试交易记录")
            return True, all_transactions
        else:
            print("\n✗ 未找到任何测试交易记录")
            return False, []
            
    except Exception as e:
        print(f"✗ 检查测试交易失败: {e}")
        return False, []

def generate_mock_transactions(analyzer):
    """
    生成模拟交易数据（用于测试）
    
    Args:
        analyzer: BinanceTransactions实例
        
    Returns:
        list: 模拟交易记录
    """
    print("\n=== 生成模拟交易数据 ===")
    
    # 生成模拟交易数据
    mock_transactions = []
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
    
    # 生成过去30天的模拟交易
    end_date = datetime.now(timezone.utc)
    start_date = end_date - pd.Timedelta(days=30)
    
    for symbol in symbols:
        # 每个交易对生成5-10笔交易
        num_trades = np.random.randint(5, 11)
        
        for i in range(num_trades):
            # 随机生成交易时间
            trade_time = start_date + pd.Timedelta(
                seconds=np.random.randint(0, int((end_date - start_date).total_seconds()))
            )
            
            # 随机生成交易参数
            side = np.random.choice(['buy', 'sell'])
            amount = np.random.uniform(0.001, 0.1)  # 交易数量
            base_price = 40000 if 'BTC' in symbol else 2500 if 'ETH' in symbol else 300
            price = base_price * (1 + np.random.uniform(-0.05, 0.05))  # 价格波动±5%
            
            # 生成交易记录
            mock_transaction = {
                'id': f"mock_{symbol.replace('/', '')}_{int(trade_time.timestamp())}_{i}",
                'order': f"mock_order_{int(trade_time.timestamp())}_{i}",
                'datetime': trade_time.isoformat(),
                'timestamp': int(trade_time.timestamp() * 1000),
                'symbol': symbol,
                'type': 'market',
                'side': side,
                'amount': amount,
                'price': price,
                'cost': amount * price,
                'fee': {
                    'cost': amount * price * 0.001,  # 0.1% 手续费
                    'currency': 'USDT'
                }
            }
            
            mock_transactions.append(mock_transaction)
    
    print(f"✓ 生成了 {len(mock_transactions)} 条模拟交易记录")
    return mock_transactions

def query_test_transactions(analyzer, days=30):
    """
    查询测试交易记录
    
    Args:
        analyzer: BinanceTransactions实例
        days: 查询天数
        
    Returns:
        dict: 格式化的交易数据
    """
    print(f"\n=== 查询最近{days}天的交易记录 ===")
    
    try:
        # 获取所有交易记录
        transactions = analyzer.get_all_transactions(days=days)
        
        if not transactions:
            print("未找到交易记录")
            return {
                'transactions': pd.DataFrame(),
                'positions': pd.DataFrame(),
                'returns': pd.Series()
            }
        
        # 转换为pyfolio格式
        transactions_df = analyzer.transactions_to_pyfolio_format(transactions)
        
        # 获取持仓信息
        positions = analyzer.get_positions()
        positions_df = analyzer.positions_to_pyfolio_format(positions, transactions_df)
        
        # 计算收益率
        returns_series = analyzer.calculate_returns(transactions_df)
        
        # 显示统计信息
        print(f"\n📊 交易统计:")
        print(f"总交易笔数: {len(transactions_df)}")
        
        if not transactions_df.empty:
            print(f"总交易额: {transactions_df['txn_volume'].sum():.2f} USDT")
            print(f"总交易数量: {transactions_df['txn_shares'].sum():.6f}")
            
            # 简化的统计信息（因为新格式没有symbol列）
            print(f"\n交易汇总:")
            print(f"平均交易额: {transactions_df['txn_volume'].mean():.2f} USDT")
            print(f"最大交易额: {transactions_df['txn_volume'].max():.2f} USDT")
            print(f"最小交易额: {transactions_df['txn_volume'].min():.2f} USDT")
        
        if not positions_df.empty:
            print(f"\n📈 当前持仓:")
            print(positions_df)
        
        if not returns_series.empty:
            print(f"\n💰 收益率统计:")
            print(f"总收益率: {(returns_series.sum() * 100):.2f}%")
            print(f"平均日收益率: {(returns_series.mean() * 100):.4f}%")
            print(f"收益率标准差: {(returns_series.std() * 100):.4f}%")
        
        return {
            'transactions': transactions_df,
            'positions': positions_df,
            'returns': returns_series
        }
        
    except Exception as e:
        print(f"✗ 查询交易记录失败: {e}")
        return {
            'transactions': pd.DataFrame(),
            'positions': pd.DataFrame(),
            'returns': pd.Series()
        }

def format_pyfolio_data(transactions_df, positions_df, returns_series):
    """
    整理数据为pyfolio格式并保存
    
    Args:
        transactions_df: 交易数据DataFrame
        positions_df: 持仓数据DataFrame
        returns_series: 收益率Series
    """
    print("\n=== 整理数据为pyfolio格式 ===")
    
    try:
        # 保存到CSV文件
        if not transactions_df.empty:
            transactions_df.to_csv('pyfolio_transactions.csv')
            print("✓ 交易数据已保存到 pyfolio_transactions.csv")
            
            # 显示pyfolio格式的交易数据示例
            print("\n📋 pyfolio格式交易数据示例:")
            print(transactions_df.head())
        
        if not positions_df.empty:
            positions_df.to_csv('pyfolio_positions.csv')
            print("✓ 持仓数据已保存到 pyfolio_positions.csv")
            
            # 显示pyfolio格式的持仓数据示例
            print("\n📋 pyfolio格式持仓数据示例:")
            print(positions_df.head())
        
        if not returns_series.empty:
            returns_series.to_csv('pyfolio_returns.csv')
            print("✓ 收益率数据已保存到 pyfolio_returns.csv")
            
            # 显示pyfolio格式的收益率数据示例
            print("\n📋 pyfolio格式收益率数据示例:")
            print(returns_series.head())
        
        # 生成pyfolio分析报告
        if not returns_series.empty:
            print(f"\n📊 pyfolio分析报告:")
            print(f"分析期间: {returns_series.index.min().date()} 至 {returns_series.index.max().date()}")
            print(f"交易天数: {len(returns_series)}")
            print(f"总收益率: {(returns_series.sum() * 100):.2f}%")
            print(f"年化收益率: {(returns_series.mean() * 252 * 100):.2f}%")
            print(f"年化波动率: {(returns_series.std() * np.sqrt(252) * 100):.2f}%")
            print(f"夏普比率: {(returns_series.mean() / returns_series.std() * np.sqrt(252)):.2f}")
            
            # 最大回撤
            cumulative_returns = (1 + returns_series).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            print(f"最大回撤: {(max_drawdown * 100):.2f}%")
        
    except Exception as e:
        print(f"✗ 整理pyfolio数据失败: {e}")

def main_example():
    """
    主要示例函数：完整演示所有功能
    """
    print("币安交易记录获取器 - 完整示例")
    print("=" * 60)
    
    try:
        # 1. 创建分析器实例
        print("\n🚀 初始化币安API连接...")
        analyzer = BinanceTransactions()
        
        # 2. 检查API密钥权限
        permissions = check_api_permissions(analyzer)
        
        # 检查基本权限
        if not permissions['can_read_trades']:
            print("\n❌ API密钥缺少交易记录读取权限，无法继续")
            return
        
        # 3. 检查账户是否有测试交易
        has_transactions, existing_transactions = check_test_transactions(analyzer, days=7)
        
        # 4. 如果没有测试交易，生成模拟交易
        if not has_transactions:
            print("\n⚠ 未找到测试交易，生成模拟交易数据...")
            mock_transactions = generate_mock_transactions(analyzer)
            
            # 将模拟交易转换为DataFrame格式
            mock_df = analyzer.transactions_to_pyfolio_format(mock_transactions)
            print("✓ 模拟交易数据生成完成")
        else:
            print("\n✓ 找到现有交易记录，使用真实数据")
        
        # 5. 查询测试交易记录
        results = query_test_transactions(analyzer, days=30)
        
        # 6. 整理数据为pyfolio格式
        format_pyfolio_data(
            results['transactions'],
            results['positions'],
            results['returns']
        )
        
        print("\n" + "=" * 60)
        print("✅ 完整示例运行完成！")
        print("📁 生成的文件:")
        print("  - pyfolio_transactions.csv (交易数据)")
        print("  - pyfolio_positions.csv (持仓数据)")
        print("  - pyfolio_returns.csv (收益率数据)")
        print("\n💡 提示: 这些文件可以直接用于pyfolio进行投资组合分析")
        
    except Exception as e:
        print(f"\n❌ 示例运行出错: {e}")
        logger.error(f"详细错误信息: {e}", exc_info=True)

def example_basic_usage():
    """基本使用示例（保留原有功能）"""
    print("\n=== 基本使用示例 ===")
    
    try:
        # 创建分析器实例
        analyzer = BinanceTransactions()
        
        # 获取最近30天的所有交易数据
        results = analyzer.run_analysis(days=30)
        
        # 显示结果
        print("\n交易记录:")
        if not results['transactions'].empty:
            print(results['transactions'].head())
        
        print("\n持仓信息:")
        if not results['positions'].empty:
            print(results['positions'])
        
        print("\n收益率序列:")
        if not results['returns'].empty:
            print(results['returns'].head())
            
    except Exception as e:
        print(f"示例运行出错: {e}")

def example_specific_symbol():
    """特定交易对示例（保留原有功能）"""
    print("\n=== 特定交易对示例 ===")
    
    try:
        analyzer = BinanceTransactions()
        
        # 只分析BTC/USDT交易对
        results = analyzer.run_analysis(symbol='BTC/USDT', days=7)
        
        print(f"\nBTC/USDT 交易记录数量: {len(results['transactions'])}")
        
        if not results['transactions'].empty:
            # 计算统计信息
            total_volume = results['transactions']['txn_volume'].sum()
            total_shares = results['transactions']['txn_shares'].sum()
            
            print(f"总交易额: {total_volume:.2f} USDT")
            print(f"总交易数量: {total_shares:.6f}")
            
    except Exception as e:
        print(f"特定交易对示例出错: {e}")

def example_manual_data_processing():
    """手动数据处理示例（保留原有功能）"""
    print("\n=== 手动数据处理示例 ===")
    
    try:
        analyzer = BinanceTransactions()
        
        # 手动获取数据
        transactions = analyzer.get_all_transactions(days=7)
        positions = analyzer.get_positions()
        
        # 转换为pyfolio格式
        transactions_df = analyzer.transactions_to_pyfolio_format(transactions)
        positions_df = analyzer.positions_to_pyfolio_format(positions, transactions_df)
        
        # 自定义分析
        if not transactions_df.empty:
            # 检查可用的列名
            print(f"\n可用列名: {list(transactions_df.columns)}")
            
            # 计算总体统计信息（因为新格式没有symbol列）
            total_volume = transactions_df['txn_volume'].sum()
            total_shares = transactions_df['txn_shares'].sum()
            
            print("\n交易统计信息:")
            print(f"总交易额: {total_volume:.2f} USDT")
            print(f"总交易数量: {total_shares:.6f}")
            print(f"平均交易额: {total_volume/len(transactions_df):.2f} USDT")
            print(f"交易笔数: {len(transactions_df)}")
            
    except Exception as e:
        print(f"手动数据处理示例出错: {e}")

if __name__ == "__main__":
    print("币安交易记录获取器 - 使用示例")
    print("=" * 50)
    
    # 运行主要示例（包含所有新功能）
    main_example()
    
    print("\n" + "=" * 50)
    print("运行原有示例...")
    
    # 运行原有示例
    example_basic_usage()
    example_specific_symbol()
    example_manual_data_processing()
    
    print("\n" + "=" * 50)
    print("所有示例运行完成！")
    print("请确保已正确配置.env文件中的API密钥。")
