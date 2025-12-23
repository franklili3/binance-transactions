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
from datetime import datetime, timezone, timedelta
import ccxt
from dotenv import load_dotenv
import logging
import requests

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
        获取所有交易记录（支持分页下载）
        
        Args:
            symbol (str): 交易对，如'BTC/USDT'
            since (int): 开始时间戳（毫秒）
            limit (int): 每页限制数量（默认1000）
            days (int): 天数（用于计算since）
            
        Returns:
            list: 交易记录列表
        """
        try:
            # 如果没有提供since参数，使用2025-4-1作为默认开始日期
            if not since:
                if days:
                    since = int((datetime.now(timezone.utc) - pd.Timedelta(days=days)).timestamp() * 1000)
                else:
                    since = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
            
            # 设置默认每页限制
            if limit is None:
                limit = 1000  # 币安API的最大限制
            
            # 如果没有指定交易对，尝试获取主要交易对的交易记录
            if not symbol:
                major_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
                all_transactions = []
                
                for sym in major_symbols:
                    try:
                        logger.debug(f"尝试获取 {sym} 的交易记录")
                        sym_transactions = self._get_transactions_with_pagination(sym, since, limit)
                        if sym_transactions:
                            all_transactions.extend(sym_transactions)
                            logger.info(f"获取到 {sym} 的 {len(sym_transactions)} 条交易记录")
                    except Exception as e:
                        logger.debug(f"获取 {sym} 交易记录失败: {e}")
                        continue
                
                logger.info(f"总共获取到 {len(all_transactions)} 条交易记录")
                return all_transactions
            else:
                # 指定了交易对，使用分页获取
                logger.debug(f"使用分页获取交易记录，参数: symbol={symbol}, since={since}, limit={limit}")
                transactions = self._get_transactions_with_pagination(symbol, since, limit)
                
                # 验证返回的数据
                if transactions is None:
                    logger.warning("分页获取交易记录返回None，返回空列表")
                    return []
                
                if not isinstance(transactions, list):
                    logger.warning(f"分页获取交易记录返回非列表类型: {type(transactions)}，返回空列表")
                    return []
                
                logger.info(f"分页获取到 {len(transactions)} 条交易记录")
                return transactions
                
        except Exception as e:
            logger.error(f"获取交易记录失败: {e}")
            logger.debug(f"错误详情: {type(e).__name__}: {str(e)}")
            return []
    
    def _get_transactions_with_pagination(self, symbol, since, limit=1000):
        """
        分页获取交易记录
        
        Args:
            symbol (str): 交易对
            since (int): 开始时间戳（毫秒）
            limit (int): 每页限制数量
            
        Returns:
            list: 所有交易记录
        """
        all_transactions = []
        from_id = None
        page_count = 0
        max_pages = 50  # 防止无限循环，最多50页
        
        while True:
            try:
                page_count += 1
                logger.debug(f"获取第 {page_count} 页交易记录...")
                
                # 构建请求参数
                params = {
                    'symbol': symbol,
                    'since': since,
                    'limit': limit
                }
                
                # 如果有from_id，添加到参数中（用于分页）
                if from_id is not None:
                    params['fromId'] = from_id
                
                # 获取当前页的交易记录
                transactions = self.exchange.fetch_my_trades(**params)
                
                if not transactions:
                    logger.debug(f"第 {page_count} 页没有交易记录，停止分页")
                    break
                
                # 添加到总列表
                all_transactions.extend(transactions)
                logger.debug(f"第 {page_count} 页获取到 {len(transactions)} 条交易记录")
                
                # 检查是否还有更多数据
                if len(transactions) < limit:
                    logger.debug(f"第 {page_count} 页数据不足 {limit} 条，表示已经是最后一页")
                    break
                
                # 获取最后一条记录的ID，用于下一页
                last_transaction = transactions[-1]
                if 'id' in last_transaction:
                    from_id = int(last_transaction['id']) + 1
                    logger.debug(f"下一页从ID {from_id} 开始")
                else:
                    # 如果没有ID字段，使用时间戳分页
                    last_timestamp = last_transaction['timestamp']
                    from_id = last_timestamp + 1
                    logger.debug(f"使用时间戳分页，下一页从时间戳 {from_id} 开始")
                
                # 防止无限循环
                if page_count >= max_pages:
                    logger.warning(f"已达到最大页数限制 {max_pages}，停止分页")
                    break
                
                # 添加延迟避免API限制
                import time
                time.sleep(0.1)  # 100ms延迟
                
            except ccxt.RateLimitExceeded as e:
                logger.warning(f"遇到API限制，等待后重试: {e}")
                import time
                time.sleep(1)  # 等待1秒后重试
                continue
            except Exception as e:
                logger.error(f"获取第 {page_count} 页交易记录失败: {e}")
                break
        
        # 去重（基于交易ID和时间戳）
        unique_transactions = []
        seen_ids = set()
        seen_timestamps = set()
        
        for tx in all_transactions:
            tx_id = tx.get('id')
            tx_timestamp = tx.get('timestamp')
            
            # 使用ID或时间戳去重
            identifier = tx_id if tx_id else tx_timestamp
            if identifier not in seen_ids and identifier not in seen_timestamps:
                seen_ids.add(tx_id)
                seen_timestamps.add(tx_timestamp)
                unique_transactions.append(tx)
        
        if len(unique_transactions) < len(all_transactions):
            logger.info(f"去重后剩余 {len(unique_transactions)} 条交易记录（去重前: {len(all_transactions)} 条）")
        
        # 按时间排序
        unique_transactions.sort(key=lambda x: x['timestamp'])
        
        return unique_transactions
    
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
    
    def get_balance(self):
        """
        获取账户余额信息
        
        Returns:
            dict: 余额信息字典，包含各资产的余额
        """
        try:
            balance = self.exchange.fetch_balance()
            
            # 提取非零余额
            non_zero_balance = {}
            if 'total' in balance:
                for asset, amount in balance['total'].items():
                    if amount > 0:
                        non_zero_balance[asset] = amount
            
            logger.info(f"获取到 {len(non_zero_balance)} 个非零余额资产")
            for asset, amount in non_zero_balance.items():
                logger.info(f"{asset}: {amount}")
            
            return non_zero_balance
        except Exception as e:
            logger.error(f"获取余额信息失败: {e}")
            return {}
    
    def get_bitcoin_price_data(self, start_date=None, end_date=None, days=30):
        """
        获取比特币价格数据
        
        Args:
            start_date (str): 开始日期，格式 'YYYY-MM-DD'
            end_date (str): 结束日期，格式 'YYYY-MM-DD'
            days (int): 天数，当没有指定日期范围时使用
            
        Returns:
            pd.DataFrame: 包含日期和价格数据的DataFrame
        """
        try:
            # 如果没有指定日期范围，使用默认开始日期2025-4-1
            if not start_date and not end_date:
                end_date = datetime.now(tz=timezone.utc)
                start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
            else:
                # 转换日期字符串为datetime对象
                if start_date:
                    start_date = pd.to_datetime(start_date).tz_localize('UTC')
                if end_date:
                    end_date = pd.to_datetime(end_date).tz_localize('UTC')
                elif start_date:
                    # 只有开始日期，使用当前时间作为结束日期
                    end_date = datetime.now(tz=timezone.utc)
            
            # 转换为毫秒时间戳
            since = int(start_date.timestamp() * 1000)
            
            # 获取BTC/USDT的K线数据（日线）
            ohlcv = self.exchange.fetch_ohlcv('BTC/USDT', '1d', since=since, limit=1000)
            
            # 转换为DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('datetime', inplace=True)
            
            # 过滤日期范围
            if end_date:
                df = df[df.index <= end_date]
            
            logger.info(f"获取到 {len(df)} 天的比特币价格数据")
            logger.info(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f} USDT")
            
            return df
            
        except Exception as e:
            logger.error(f"获取比特币价格数据失败: {e}")
            # 如果API失败，尝试使用备用方法
            return self._get_bitcoin_price_fallback(start_date, end_date, days)
    
    def _get_bitcoin_price_fallback(self, start_date=None, end_date=None, days=30):
        """
        备用方法获取比特币价格数据（使用币安公开API）
        
        Args:
            start_date (datetime): 开始日期
            end_date (datetime): 结束日期
            days (int): 天数
            
        Returns:
            pd.DataFrame: 包含日期和价格数据的DataFrame
        """
        try:
            logger.info("使用币安公开API获取比特币价格数据...")
            
            # 计算日期范围，使用默认开始日期2025-4-1
            if not start_date:
                end_date = datetime.now(tz=timezone.utc)
                start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
            elif not end_date:
                end_date = datetime.now(tz=timezone.utc)
            
            # 转换为毫秒时间戳
            since = int(start_date.timestamp() * 1000)
            
            # 使用币安公开API获取K线数据
            # 币安公开API文档: https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',  # 日线数据
                'startTime': since,
                'limit': 1000  # 最大1000条
            }
            
            # 发送请求
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning("币安API返回空数据")
                return self._get_mock_bitcoin_price_data(start_date, end_date, days)
            
            # 转换为DataFrame
            # 币安K线数据格式: [开盘时间, 开盘价, 最高价, 最低价, 收盘价, 成交量, 收盘时间, ...]
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 转换数据类型
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 设置索引并过滤数据
            df.set_index('datetime', inplace=True)
            
            # 过滤日期范围
            if end_date:
                df = df[df.index <= end_date]
            
            # 只保留需要的列
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # 删除空值
            df = df.dropna()
            
            logger.info(f"使用币安公开API获取到 {len(df)} 天的比特币价格数据")
            logger.info(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f} USDT")
            
            return df
            
        except Exception as e:
            logger.error(f"币安公开API获取比特币价格数据失败: {e}")
            # 最后的备用方案：使用模拟数据
            return self._get_mock_bitcoin_price_data(start_date, end_date, days)
    
    def balance_to_pyfolio_format(self, balance_data, transactions_df=None):
        """
        将余额信息转换为pyfolio格式的positions数据
        注意：此方法已被弃用，请使用 calculate_positions_from_transactions
        
        Args:
            balance_data (dict): 余额信息字典
            transactions_df (pd.DataFrame): 交易数据，用于确定日期范围
            
        Returns:
            pd.DataFrame: pyfolio格式的持仓数据
        """
        logger.warning("balance_to_pyfolio_format方法已弃用，请使用calculate_positions_from_transactions")
        # 返回空的DataFrame，强制使用新方法
        return pd.DataFrame()
    
    def calculate_positions_from_transactions(self, symbol=None, days=30):
        """
        基于交易记录计算每日持仓变化
        
        Args:
            symbol (str): 交易对，如'BTC/USDT'
            days (int): 分析天数
            
        Returns:
            pd.DataFrame: pyfolio格式的持仓数据，包含每日持仓变化
        """
        try:
            logger.info("开始基于交易记录计算每日持仓...")
            
            # 获取原始交易数据
            since = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
            raw_transactions = self.get_all_transactions(symbol=symbol, since=since)
            
            if not raw_transactions:
                logger.warning("没有找到交易记录，返回空的持仓数据")
                return pd.DataFrame()
            
            # 获取价格数据
            start_date = pd.to_datetime(min(tx['datetime'] for tx in raw_transactions), utc=True).normalize()
            end_date = pd.Timestamp.now(tz='UTC').normalize()
            
            btc_price_df = self.get_bitcoin_price_data(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if btc_price_df.empty:
                logger.warning("无法获取价格数据，使用模拟数据")
                btc_price_df = self._get_mock_bitcoin_price_data(start_date, end_date)
            
            # 创建日期范围
            date_range = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
            positions_df = pd.DataFrame(index=date_range)
            
            # 初始化持仓追踪
            holdings = {}  # {asset: quantity}
            initial_usdt = 10000.0  # 假设初始资金
            
            # 设置初始USDT余额
            holdings['USDT'] = initial_usdt
            positions_df['USDT'] = initial_usdt
            
            # 按日期排序交易记录
            sorted_transactions = sorted(raw_transactions, key=lambda x: x['datetime'])
            
            # 逐日处理交易
            for i, date in enumerate(date_range):
                # 重置当日数据
                daily_holdings = holdings.copy()
                
                # 处理当日的所有交易
                date_transactions = [tx for tx in sorted_transactions 
                                   if pd.to_datetime(tx['datetime'], utc=True).date() == date.date()]
                
                for tx in date_transactions:
                    symbol = tx['symbol']
                    side = tx['side']
                    amount = tx['amount']
                    cost = tx['cost']
                    
                    # 解析交易对
                    if '/' in symbol:
                        base_asset, quote_asset = symbol.split('/')
                    else:
                        # 处理特殊情况，如USDT稳定币
                        continue
                    
                    # 更新持仓
                    if side == 'buy':
                        # 买入base资产，支付quote资产
                        daily_holdings[base_asset] = daily_holdings.get(base_asset, 0) + amount
                        daily_holdings[quote_asset] = daily_holdings.get(quote_asset, 0) - cost
                    else:  # sell
                        # 卖出base资产，获得quote资产
                        daily_holdings[base_asset] = daily_holdings.get(base_asset, 0) - amount
                        daily_holdings[quote_asset] = daily_holdings.get(quote_asset, 0) + cost
                
                # 更新持仓记录
                holdings = daily_holdings.copy()
                
                # 计算各资产的USDT价值
                for asset, quantity in holdings.items():
                    if quantity <= 0:
                        positions_df.loc[date, asset] = 0
                        continue
                    
                    if asset == 'USDT':
                        positions_df.loc[date, asset] = quantity
                    elif asset == 'BTC':
                        # 获取当日BTC价格
                        if date in btc_price_df.index:
                            btc_price = btc_price_df.loc[date, 'close']
                        else:
                            # 使用最近的价格
                            nearest_date = btc_price_df.index[btc_price_df.index.get_indexer([date], method='nearest')[0]]
                            btc_price = btc_price_df.loc[nearest_date, 'close']
                        positions_df.loc[date, asset] = quantity * btc_price
                    else:
                        # 其他资产使用估算价格
                        estimated_price = self._get_asset_price_estimate(asset)
                        positions_df.loc[date, asset] = quantity * estimated_price
                
                # 确保USDT列存在
                if 'USDT' not in positions_df.columns:
                    positions_df['USDT'] = 0.0
                
                # 填充缺失值为0
                positions_df.loc[date] = positions_df.loc[date].fillna(0)
            
            # 前向填充持仓（在没有交易的日期，持仓保持不变）
            positions_df = positions_df.fillna(method='ffill').fillna(0)
            
            logger.info(f"成功计算 {len(positions_df)} 天的持仓数据")
            logger.info(f"涉及的资产: {list(positions_df.columns)}")
            
            return positions_df
            
        except Exception as e:
            logger.error(f"计算每日持仓失败: {e}")
            return pd.DataFrame()
    
    def transactions_to_pyfolio_format(self, transactions):
        """
        将交易记录转换为pyfolio格式
        
        Args:
            transactions (list): ccxt格式的交易记录
            
        Returns:
            pd.DataFrame: pyfolio格式的交易数据，包含正确符号的txn_volume和txn_shares列
        """
        if not transactions:
            return pd.DataFrame()
        
        pyfolio_data = []
        for tx in transactions:
            # 计算交易金额和数量，卖出时使用负值
            if tx['side'] == 'sell':
                txn_volume = -abs(tx['cost'])  # 卖出时交易金额为负
                txn_shares = -abs(tx['amount'])  # 卖出时交易数量为负
            else:  # buy
                txn_volume = abs(tx['cost'])   # 买入时交易金额为正
                txn_shares = abs(tx['amount'])  # 买入时交易数量为正
            
            pyfolio_data.append({
                'date': pd.to_datetime(tx['datetime'], utc=True),
                'txn_volume': txn_volume,
                'txn_shares': txn_shares,
                'symbol': tx['symbol'],  # 保留symbol信息用于调试
                'side': tx['side']       # 保留side信息用于调试
            })
        
        df = pd.DataFrame(pyfolio_data)
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        # 移除调试列，只保留pyfolio需要的列
        pyfolio_df = df[['txn_volume', 'txn_shares']].copy()
        
        logger.info(f"转换了 {len(transactions)} 条交易记录")
        logger.info(f"买入交易: {len(df[df['side'] == 'buy'])} 条")
        logger.info(f"卖出交易: {len(df[df['side'] == 'sell'])} 条")
        logger.info(f"交易日期范围: {pyfolio_df.index.min()} 到 {pyfolio_df.index.max()}")
        
        return pyfolio_df
    
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
            # 使用交易数据的日期范围，获取所有唯一的日期
            unique_dates = transactions_df.index.normalize().unique()
            # 按日期排序
            date_range = pd.DatetimeIndex(sorted(unique_dates))
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
    
    def calculate_returns(self, transactions):
        """
        基于仓位和比特币价格计算每日账户净值和收益率序列
        
        Args:
            transactions (pd.DataFrame): 交易数据（只包含txn_volume和txn_shares）
            
        Returns:
            pd.Series: 收益率序列
        """
        if transactions.empty:
            return pd.Series()
        
        logger.info("开始基于仓位和比特币价格计算收益率...")
        
        # 获取比特币价格数据
        start_date = transactions.index.min().normalize()
        end_date = transactions.index.max().normalize()
        btc_price_df = self.get_bitcoin_price_data(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if btc_price_df.empty:
            logger.warning("无法获取比特币价格数据，使用简化计算方法")
            return self._calculate_simple_returns(transactions)
        
        # 获取原始交易数据以提取symbol和交易方向
        since = int(start_date.timestamp() * 1000)
        raw_transactions = self.get_all_transactions(since=since)
        
        # 计算每日持仓变化
        daily_positions = self._calculate_daily_positions(raw_transactions, btc_price_df)
        
        # 计算每日账户净值
        daily_portfolio_value = self._calculate_portfolio_value(daily_positions, btc_price_df)
        
        # 计算收益率
        returns = daily_portfolio_value.pct_change().fillna(0)
        
        logger.info(f"基于 {len(daily_portfolio_value)} 天的数据计算收益率")
        logger.info(f"收益率范围: {returns.min():.4f} - {returns.max():.4f}")
        
        return returns
    
    def _calculate_daily_positions(self, raw_transactions, btc_price_df):
        """
        计算每日持仓变化
        
        Args:
            raw_transactions (list): 原始交易记录
            btc_price_df (pd.DataFrame): 比特币价格数据
            
        Returns:
            pd.DataFrame: 每日持仓数据
        """
        # 创建日期范围
        date_range = pd.date_range(
            start=btc_price_df.index.min(),
            end=btc_price_df.index.max(),
            freq='D'
        )
        
        positions_df = pd.DataFrame(index=date_range)
        
        # 初始化持仓列
        positions_df['BTC'] = 0.0
        positions_df['USDT'] = 0.0
        
        # 添加初始USDT余额（假设有初始资金）
        initial_usdt = 10000.0  # 默认初始资金
        positions_df.loc[:, 'USDT'] = initial_usdt
        
        # 按日期处理交易，逐日更新持仓
        current_btc = 0.0
        current_usdt = initial_usdt
        
        # 先按日期排序交易记录
        sorted_transactions = sorted(raw_transactions, key=lambda x: x['datetime'])
        
        # 为每个日期处理交易
        for i, date in enumerate(date_range):
            # 处理当日的所有交易
            date_str = date.strftime('%Y-%m-%d')
            daily_transactions = [tx for tx in sorted_transactions 
                                if pd.to_datetime(tx['datetime'], utc=True).date() == date.date()]
            
            # 处理当日每笔交易
            for tx in daily_transactions:
                symbol = tx['symbol']
                side = tx['side']
                amount = tx['amount']
                cost = tx['cost']
                price = tx['price']
                
                if symbol == 'BTC/USDT':
                    if side == 'buy':
                        # 买入BTC：减少USDT，增加BTC
                        current_btc += amount
                        current_usdt -= cost
                    else:  # sell
                        # 卖出BTC：增加USDT，减少BTC
                        current_btc -= amount
                        current_usdt += cost
                elif symbol.endswith('/USDT'):
                    # 其他USDT交易对，简化处理为USDT价值变化
                    if side == 'buy':
                        current_usdt -= cost
                    else:  # sell
                        current_usdt += cost
            
            # 更新当日持仓
            positions_df.loc[date, 'BTC'] = current_btc
            positions_df.loc[date, 'USDT'] = current_usdt
        
        return positions_df
    
    def _calculate_portfolio_value(self, daily_positions, btc_price_df):
        """
        计算每日投资组合价值
        
        Args:
            daily_positions (pd.DataFrame): 每日持仓数据
            btc_price_df (pd.DataFrame): 比特币价格数据
            
        Returns:
            pd.Series: 每日投资组合价值
        """
        portfolio_values = []
        
        for date in daily_positions.index:
            daily_value = 0.0
            
            # 获取当日持仓
            positions = daily_positions.loc[date]
            
            # 计算各资产价值
            for asset, amount in positions.items():
                if amount == 0:
                    continue
                    
                if asset == 'USDT':
                    # USDT直接计入价值
                    daily_value += amount
                elif asset == 'BTC':
                    # 获取当日BTC价格
                    if date in btc_price_df.index:
                        btc_price = btc_price_df.loc[date, 'close']
                        daily_value += amount * btc_price
                    else:
                        # 如果没有当日价格，使用最近的价格
                        nearest_date = btc_price_df.index[btc_price_df.index.get_indexer([date], method='nearest')[0]]
                        btc_price = btc_price_df.loc[nearest_date, 'close']
                        daily_value += amount * btc_price
                else:
                    # 其他资产的简化处理（使用估算价格）
                    estimated_price = self._get_asset_price_estimate(asset)
                    daily_value += amount * estimated_price
            
            portfolio_values.append(daily_value)
        
        return pd.Series(portfolio_values, index=daily_positions.index)
    
    def _get_asset_price_estimate(self, asset):
        """
        获取资产价格估算（简化处理）
        
        Args:
            asset (str): 资产符号
            
        Returns:
            float: 估算价格（USDT）
        """
        # 简化的价格估算表
        price_estimates = {
            'ETH': 3000.0,
            'BNB': 300.0,
            'ADA': 0.5,
            'SOL': 100.0,
            'DOT': 10.0,
            'LINK': 15.0,
            'MATIC': 0.8,
            'AVAX': 30.0,
            'UNI': 6.0,
            'ATOM': 10.0
        }
        
        return price_estimates.get(asset, 1.0)  # 默认价格为1 USDT
    
    def _get_mock_bitcoin_price_data(self, start_date=None, end_date=None, days=30):
        """
        生成模拟比特币价格数据（当所有API都失败时使用）
        
        Args:
            start_date (datetime): 开始日期
            end_date (datetime): 结束日期
            days (int): 天数
            
        Returns:
            pd.DataFrame: 包含日期和价格数据的DataFrame
        """
        try:
            logger.info("生成模拟比特币价格数据...")
            
            # 计算日期范围，使用默认开始日期2025-4-1
            if not start_date:
                end_date = datetime.now(tz=timezone.utc)
                start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
            elif not end_date:
                end_date = datetime.now(tz=timezone.utc)
            
            # 创建日期范围
            date_range = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
            
            # 生成模拟价格数据
            # 假设初始价格为95000 USDT，随机波动
            np.random.seed(42)  # 固定种子以确保可重现性
            base_price = 95000.0
            price_changes = np.random.normal(0, 0.02, len(date_range))  # 2%的日波动率
            prices = [base_price]
            
            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1000))  # 最低价格限制为1000 USDT
            
            # 创建DataFrame
            mock_data = []
            for i, date in enumerate(date_range):
                price = prices[i]
                # 生成合理的OHLC数据
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = low + (high - low) * np.random.random()
                volume = np.random.uniform(1000, 5000)  # 模拟交易量
                
                mock_data.append({
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            df = pd.DataFrame(mock_data, index=date_range)
            
            logger.info(f"生成 {len(df)} 天的模拟比特币价格数据")
            logger.info(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f} USDT")
            logger.warning("这是模拟数据，仅用于测试目的")
            
            return df
            
        except Exception as e:
            logger.error(f"生成模拟比特币价格数据失败: {e}")
            return pd.DataFrame()

    def _calculate_simple_returns(self, transactions):
        """
        简化的收益率计算方法（当无法获取价格数据时使用）
        
        Args:
            transactions (pd.DataFrame): 交易数据
            
        Returns:
            pd.Series: 收益率序列
        """
        logger.info("使用简化方法计算收益率...")
        
        # 按日期排序
        transactions_sorted = transactions.sort_index()
        
        # 计算每日的盈亏
        daily_pnl = []
        portfolio_values = []
        
        # 初始化投资组合价值
        current_portfolio_value = 0.0
        
        # 使用更兼容的方式按日期分组
        transactions_sorted['date_only'] = transactions_sorted.index.date
        for date, group in transactions_sorted.groupby('date_only'):
            # 简化的收益率计算：基于交易金额的变化
            day_volume = group['txn_volume'].sum()
            day_shares = group['txn_shares'].sum()
            
            # 简化假设：每日投资组合价值变化基于交易金额
            # 这里使用一个简化的收益率计算方法
            if day_volume != 0:
                # 基于交易金额的简单收益率计算
                portfolio_value_change = day_shares * 100  # 简化假设每个share价值100 USDT
                current_portfolio_value += portfolio_value_change
            else:
                portfolio_value_change = 0
            
            # 计算收益率（基于前一日价值）
            if len(portfolio_values) > 0:
                daily_return = portfolio_value_change / portfolio_values[-1] if portfolio_values[-1] != 0 else 0
            else:
                daily_return = 0
            
            portfolio_values.append(current_portfolio_value)
            daily_pnl.append({
                'date': pd.to_datetime(date),
                'return': daily_return,
                'portfolio_value': current_portfolio_value
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
        
        # 使用默认开始时间2025-4-1
        since = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        
        # 获取数据
        transactions = self.get_all_transactions(symbol=symbol, since=since)
        balance_data = self.get_balance()
        
        # 转换为pyfolio格式
        transactions_df = self.transactions_to_pyfolio_format(transactions)
        
        # 使用新的方法计算每日持仓变化
        logger.info("使用新的方法计算每日持仓变化...")
        positions_df = self.calculate_positions_from_transactions(symbol=symbol, days=days)
        
        # 如果新方法失败，回退到旧方法
        if positions_df.empty:
            logger.warning("新方法计算持仓失败，回退到旧方法...")
            if balance_data:
                positions_df = self.balance_to_pyfolio_format(balance_data, transactions_df)
            else:
                positions_df = self.positions_to_pyfolio_format(None, transactions_df)
        else:
            logger.info("新方法成功计算持仓数据")
        
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
        logger.info(f"余额资产数量: {len(balance_data)}")
        
        if not transactions_df.empty:
            logger.info(f"总交易额: {transactions_df['txn_volume'].sum():.2f} USDT")
            logger.info(f"总交易数量: {transactions_df['txn_shares'].sum():.6f}")
        
        if not positions_df.empty:
            # 检查是否有USDT列，如果没有则使用cash列
            if 'USDT' in positions_df.columns:
                total_value = positions_df.drop('USDT', axis=1).sum().sum() + positions_df['USDT'].sum()
                logger.info(f"总持仓价值: {total_value:.2f} USDT")
                logger.info(f"USDT余额: {positions_df['USDT'].sum():.2f} USDT")
            else:
                total_value = positions_df.drop('cash', axis=1).sum().sum() + positions_df['cash'].sum()
                logger.info(f"总持仓价值: {total_value:.2f} USDT")
                logger.info(f"现金余额: {positions_df['cash'].sum():.2f} USDT")
            
            # 显示持仓变化统计
            logger.info("=== 持仓变化统计 ===")
            for asset in positions_df.columns:
                if asset in ['USDT', 'cash']:
                    continue
                asset_values = positions_df[asset]
                if asset_values.max() > 0:
                    logger.info(f"{asset}: 最小值 {asset_values.min():.2f}, 最大值 {asset_values.max():.2f}, 平均值 {asset_values.mean():.2f}")
        
        if not returns_series.empty:
            logger.info(f"总收益率: {(returns_series.sum() * 100):.2f}%")
            logger.info(f"平均日收益率: {(returns_series.mean() * 100):.4f}%")
        
        return {
            'transactions': transactions_df,
            'positions': positions_df,
            'returns': returns_series,
            'balance': balance_data
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
