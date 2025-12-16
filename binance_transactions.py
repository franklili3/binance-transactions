#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安带单交易记录获取器
用于获取币安账户的交易记录并整理成pyfolio格式

本程序仅用于学习交流，请勿用于非法用途。
本程序不保证数据的准确性，使用本程序产生的任何后果由使用者自行承担。
本程序不保证数据的实时性，数据可能会有一定的延迟。
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import ccxt
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 改为DEBUG级别以获取更多信息
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('binance_trader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BinanceTransactions:
    def __init__(self):
        """初始化币安API连接"""
        load_dotenv()
        
        # 获取API密钥
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not secret_key:
            raise ValueError("请在.env文件中设置BINANCE_API_KEY和BINANCE_SECRET_KEY")
        
        # 检查是否使用测试网
        testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
        
        # 初始化ccxt交易所对象
        if testnet:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret_key,
                'sandbox': True,
                'enableRateLimit': True,
            })
            logger.info("使用币安测试网")
        else:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret_key,
                'enableRateLimit': True,
            })
            logger.info("使用币安生产环境")
        
        # 测试连接
        self._test_connection()
    
    def _test_connection(self):
        """测试API连接"""
        try:
            # 首先尝试获取服务器时间（不需要认证）
            server_time = self.exchange.fetch_time()
            logger.info(f"币安服务器时间: {datetime.fromtimestamp(server_time/1000)}")
            
            # 然后尝试获取账户信息（需要认证）
            balance = self.exchange.fetch_balance()
            logger.info("API连接成功")
            
            # 检查账户权限
            if 'info' in balance:
                account_type = balance['info'].get('accountType', 'UNKNOWN')
                logger.info(f"账户类型: {account_type}")
            
            # 检查API权限
            self._check_api_permissions()
            
        except ccxt.AuthenticationError as e:
            logger.error(f"API认证失败: {e}")
            logger.error("请检查API密钥是否正确，或者是否有足够的权限")
            raise
        except ccxt.PermissionDenied as e:
            logger.error(f"API权限不足: {e}")
            logger.error("请确保API密钥有以下权限：现货交易、读取信息")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"网络连接错误: {e}")
            logger.error("请检查网络连接")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"交易所错误: {e}")
            logger.error("可能是API配置问题或交易所限制")
            raise
        except Exception as e:
            logger.error(f"未知错误: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            raise
    
    def _check_api_permissions(self):
        """检查API权限"""
        try:
            logger.info("检查API权限...")
            
            # 检查账户信息权限
            try:
                account_info = self.exchange.fetch_account()
                logger.info("✓ 账户信息权限 - 正常")
            except Exception as e:
                logger.warning(f"✗ 账户信息权限 - 失败: {e}")
            
            # 检查交易历史权限
            try:
                # 尝试获取最近的交易记录
                trades = self.exchange.fetch_my_trades('BTC/USDT', limit=1)
                logger.info("✓ 交易历史权限 - 正常")
            except Exception as e:
                logger.warning(f"✗ 交易历史权限 - 失败: {e}")
            
            # 检查订单权限
            try:
                orders = self.exchange.fetch_orders('BTC/USDT', limit=1)
                logger.info("✓ 订单权限 - 正常")
            except Exception as e:
                logger.warning(f"✗ 订单权限 - 失败: {e}")
            
            # 检查余额权限
            try:
                balance = self.exchange.fetch_balance()
                logger.info("✓ 余额权限 - 正常")
            except Exception as e:
                logger.warning(f"✗ 余额权限 - 失败: {e}")
                
        except Exception as e:
            logger.warning(f"权限检查过程中出错: {e}")
    
    def get_all_transactions(self, symbol=None, since=None, limit=None, days=None):
        """
        获取所有交易记录
        
        Args:
            symbol (str): 交易对，如'BTC/USDT'
            since (int): 开始时间戳（毫秒）
            limit (int): 限制数量
            days (int): 天数（用于计算since）
            
        Returns:
            list: 交易记录列表
        """
        try:
            # 如果提供了days参数，计算since
            if days and not since:
                since = int((datetime.now() - pd.Timedelta(days=days)).timestamp() * 1000)
            
            # 如果没有指定交易对，尝试获取主要交易对的交易记录
            if not symbol:
                major_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
                all_transactions = []
                
                for sym in major_symbols:
                    try:
                        logger.debug(f"尝试获取 {sym} 的交易记录")
                        sym_transactions = self.exchange.fetch_my_trades(symbol=sym, since=since, limit=limit)
                        if sym_transactions:
                            all_transactions.extend(sym_transactions)
                            logger.info(f"获取到 {sym} 的 {len(sym_transactions)} 条交易记录")
                    except Exception as e:
                        logger.debug(f"获取 {sym} 交易记录失败: {e}")
                        continue
                
                logger.info(f"总共获取到 {len(all_transactions)} 条交易记录")
                return all_transactions
            else:
                # 指定了交易对，直接获取
                logger.debug(f"调用fetch_my_trades，参数: symbol={symbol}, since={since}, limit={limit}")
                transactions = self.exchange.fetch_my_trades(symbol=symbol, since=since, limit=limit)
                
                # 验证返回的数据
                if transactions is None:
                    logger.warning("fetch_my_trades返回None，返回空列表")
                    return []
                
                if not isinstance(transactions, list):
                    logger.warning(f"fetch_my_trades返回非列表类型: {type(transactions)}，返回空列表")
                    return []
                
                logger.info(f"获取到 {len(transactions)} 条交易记录")
                return transactions
                
        except Exception as e:
            logger.error(f"获取交易记录失败: {e}")
            logger.debug(f"错误详情: {type(e).__name__}: {str(e)}")
            return []
    
    def get_all_orders(self, symbol=None, since=None, limit=None):
        """
        获取所有订单记录
        
        Args:
            symbol (str): 交易对，如'BTC/USDT'
            since (int): 开始时间戳（毫秒）
            limit (int): 限制数量
            
        Returns:
            list: 订单记录列表
        """
        try:
            # fetch_orders 需要指定交易对
            if not symbol:
                logger.warning("获取订单记录需要指定交易对，跳过订单获取")
                return []
            
            orders = self.exchange.fetch_orders(symbol=symbol, since=since, limit=limit)
            logger.info(f"获取到 {len(orders)} 条订单记录")
            return orders
        except Exception as e:
            logger.error(f"获取订单记录失败: {e}")
            return []
    
    def get_positions(self):
        """
        获取当前持仓信息
        
        Returns:
            list: 持仓信息列表
        """
        try:
            # 检查是否为测试网
            if hasattr(self.exchange, 'sandbox') and self.exchange.sandbox:
                logger.warning("测试网不支持期货持仓信息，返回空列表")
                return []
            
            positions = self.exchange.fetch_positions()
            logger.info(f"获取到 {len(positions)} 个持仓信息")
            return positions
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}")
            return []
    
    def transactions_to_pyfolio_format(self, transactions):
        """
        将交易记录转换为pyfolio格式
        
        Args:
            transactions (list): ccxt格式的交易记录
            
        Returns:
            pd.DataFrame: pyfolio格式的交易数据，只包含txn_volume和txn_shares列
        """
        if not transactions:
            return pd.DataFrame()
        
        pyfolio_data = []
        for tx in transactions:
            # 计算交易金额和数量
            txn_volume = tx['cost']  # 交易金额
            txn_shares = tx['amount']  # 交易数量
            
            pyfolio_data.append({
                'date': pd.to_datetime(tx['datetime'], utc=True),
                'txn_volume': txn_volume,
                'txn_shares': txn_shares
            })
        
        df = pd.DataFrame(pyfolio_data)
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    def positions_to_pyfolio_format(self, positions, transactions_df=None):
        """
        将持仓信息转换为pyfolio格式
        
        Args:
            positions (list): ccxt格式的持仓信息
            transactions_df (pd.DataFrame): 交易数据，用于计算持仓价值
            
        Returns:
            pd.DataFrame: pyfolio格式的持仓数据，每个交易对作为单独的列，包含现金列
        """
        if not positions and (transactions_df is None or transactions_df.empty):
            return pd.DataFrame()
        
        # 创建持仓数据字典，key为交易对symbol，value为持仓价值
        positions_data = {}
        
        # 如果有交易数据，从交易数据计算持仓
        if transactions_df is not None and not transactions_df.empty:
            # 从交易数据中提取symbol信息（需要从原始交易数据中获取）
            # 由于新格式只包含txn_volume和txn_shares，我们需要重新获取原始交易数据来提取symbol
            try:
                # 重新获取原始交易数据以提取symbol信息
                since = int((datetime.now() - pd.Timedelta(days=30)).timestamp() * 1000)
                raw_transactions = self.get_all_transactions(since=since)
                
                # 按symbol汇总持仓
                symbol_positions = {}
                for tx in raw_transactions:
                    symbol = tx['symbol']
                    if symbol not in symbol_positions:
                        symbol_positions[symbol] = {'amount': 0, 'total_cost': 0}
                    
                    # 根据买卖方向调整持仓
                    if tx['side'] == 'buy':
                        symbol_positions[symbol]['amount'] += tx['amount']
                        symbol_positions[symbol]['total_cost'] += tx['cost']
                    else:  # sell
                        symbol_positions[symbol]['amount'] -= tx['amount']
                        symbol_positions[symbol]['total_cost'] -= tx['cost']
                
                # 计算每个symbol的当前持仓价值
                for symbol, pos_data in symbol_positions.items():
                    if pos_data['amount'] != 0:
                        # 使用平均成本作为当前价值的近似
                        avg_price = pos_data['total_cost'] / pos_data['amount'] if pos_data['amount'] != 0 else 0
                        current_value = abs(pos_data['amount']) * avg_price
                        # 使用symbol的基础资产名称作为列名（去掉/USDT等）
                        base_symbol = symbol.split('/')[0]
                        positions_data[base_symbol] = current_value
                        
            except Exception as e:
                logger.warning(f"从交易数据计算持仓失败: {e}")
                # 如果失败，使用简化的方法
                total_volume = transactions_df['txn_volume'].sum()
                if total_volume > 0:
                    # 假设主要是BTC/USDT交易，使用BTC作为主要持仓
                    positions_data['BTC'] = total_volume
        
        # 如果有真实的持仓数据，合并进来
        if positions:
            for pos in positions:
                if float(pos['contracts']) != 0:  # 只处理有持仓的
                    symbol = pos['symbol'].split('/')[0] if '/' in pos['symbol'] else pos['symbol']
                    # 使用标记价格计算持仓价值
                    mark_price = float(pos['markPrice']) if pos['markPrice'] else 0
                    contracts = float(pos['contracts'])
                    position_value = abs(contracts) * mark_price
                    positions_data[symbol] = position_value
        
        # 如果没有持仓数据，创建空的DataFrame
        if not positions_data:
            return pd.DataFrame()
        
        # 创建时间序列（与交易数据的日期范围一致）
        if transactions_df is not None and not transactions_df.empty:
            # 使用交易数据的日期范围
            start_date = transactions_df.index.min()
            end_date = transactions_df.index.max()
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        else:
            # 如果没有交易数据，使用最近30天的日期范围
            end_date = pd.Timestamp.now(tz='UTC')
            date_range = pd.date_range(start=end_date - pd.Timedelta(days=30), end=end_date, freq='D')
        
        # 创建positions DataFrame
        positions_df = pd.DataFrame(index=date_range)
        
        # 为每个资产添加持仓价值列
        for symbol, value in positions_data.items():
            # 假设持仓在期间保持不变（简化处理）
            positions_df[symbol] = value
        
        # 添加现金列（假设现金余额为0，可以根据实际情况调整）
        positions_df['cash'] = 0.0
        
        return positions_df
    
    def calculate_returns(self, transactions, initial_capital=10000):
        """
        计算收益率序列
        
        Args:
            transactions (pd.DataFrame): 交易数据（只包含txn_volume和txn_shares）
            initial_capital (float): 初始资金
            
        Returns:
            pd.Series: 收益率序列
        """
        if transactions.empty:
            return pd.Series()
        
        # 按日期排序
        transactions_sorted = transactions.sort_index()
        
        # 计算每日的盈亏
        daily_pnl = []
        current_capital = initial_capital
        
        # 使用更兼容的方式按日期分组
        transactions_sorted['date_only'] = transactions_sorted.index.date
        for date, group in transactions_sorted.groupby('date_only'):
            # 简化的收益率计算：基于交易金额的变化
            day_volume = group['txn_volume'].sum()
            day_shares = group['txn_shares'].sum()
            
            # 假设买入为正，卖出为负（简化处理）
            # 这里使用一个简化的收益率计算方法
            if day_volume != 0:
                # 基于交易金额的简单收益率计算
                daily_return = (day_shares * 0.01) / current_capital  # 简化假设1%的价格变化
            else:
                daily_return = 0
            
            current_capital += day_volume * daily_return
            daily_pnl.append({
                'date': pd.to_datetime(date),
                'return': daily_return,
                'capital': current_capital
            })
        
        # 删除临时列
        transactions_sorted.drop('date_only', axis=1, inplace=True)
        
        returns_df = pd.DataFrame(daily_pnl)
        returns_df.set_index('date', inplace=True)
        
        return returns_df['return']
    
    def save_to_csv(self, data, filename):
        """
        保存数据到CSV文件
        
        Args:
            data (pd.DataFrame): 要保存的数据
            filename (str): 文件名
        """
        try:
            data.to_csv(filename)
            logger.info(f"数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
    
    def run_analysis(self, symbol=None, days=30):
        """
        运行完整分析
        
        Args:
            symbol (str): 交易对，如'BTC/USDT'
            days (int): 分析天数
        """
        logger.info("开始获取币安交易数据...")
        
        # 计算开始时间
        since = int((datetime.now() - pd.Timedelta(days=days)).timestamp() * 1000)
        
        # 获取数据（只获取交易记录）
        transactions = self.get_all_transactions(symbol=symbol, since=since)
        
        # 转换为pyfolio格式
        transactions_df = self.transactions_to_pyfolio_format(transactions)
        positions_df = self.positions_to_pyfolio_format(None, transactions_df)
        returns_series = self.calculate_returns(transactions_df)
        
        # 保存数据
        if not transactions_df.empty:
            self.save_to_csv(transactions_df, 'transactions_pyfolio.csv')
        
        if not positions_df.empty:
            self.save_to_csv(positions_df, 'positions_pyfolio.csv')
        
        if not returns_series.empty:
            self.save_to_csv(returns_series, 'returns_pyfolio.csv')
        
        # 打印摘要
        logger.info("=== 数据摘要 ===")
        logger.info(f"交易记录数量: {len(transactions)}")
        
        if not transactions_df.empty:
            logger.info(f"总交易额: {transactions_df['txn_volume'].sum():.2f} USDT")
            logger.info(f"总交易数量: {transactions_df['txn_shares'].sum():.6f}")
        
        if not returns_series.empty:
            logger.info(f"总收益率: {(returns_series.sum() * 100):.2f}%")
            logger.info(f"平均日收益率: {(returns_series.mean() * 100):.4f}%")
        
        return {
            'transactions': transactions_df,
            'positions': positions_df,
            'returns': returns_series
        }

def main():
    """主函数"""
    try:
        # 创建分析器实例
        analyzer = BinanceTransactions()
        
        # 运行分析（可以指定交易对和天数）
        results = analyzer.run_analysis(symbol=None, days=30)
        
        logger.info("分析完成！数据已保存到CSV文件。")
        
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        logger.info("请检查.env文件中的API密钥配置")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
