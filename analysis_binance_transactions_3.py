#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安交易记录分析器（增强版）
用于分析币安交易记录CSV文件并计算收益率
新增功能：从本地BTC价格文件获取比特币价格数据，并保存为pyfolio格式
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timezone, timedelta
import warnings

# 配置日志 - 输出到文件和控制台
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO, 
    format=log_format,
    handlers=[
        logging.FileHandler('binance_trader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 忽略警告
warnings.filterwarnings('ignore')

class BinanceTransactionAnalyzer:
    def __init__(self, csv_file_path: str, btc_price_file_path: str = 'btc_prices.csv'):
        """初始化分析器"""
        self.csv_file = csv_file_path
        self.btc_price_file = btc_price_file_path
        self.raw_data = None
        self.processed_data = None
        self.asset_balances = {}
        self.daily_portfolio_value = None
        self.btc_price_data = None
        self.spot_lead_balances = {}  # 新增：单独跟踪Spot Lead账户的余额
        
    def load_data(self):
        """加载CSV数据"""
        try:
            self.raw_data = pd.read_csv(self.csv_file)
            logger.info(f"成功加载 {len(self.raw_data)} 条交易记录")
            
            # 检查必要的列是否存在
            required_columns = ['UTC_Time', 'Account', 'Operation', 'Coin', 'Change', 'Remark']
            missing_columns = [col for col in required_columns if col not in self.raw_data.columns]
            if missing_columns:
                raise ValueError(f"缺少必要的列: {missing_columns}")
            
            logger.info(f"交易记录时间范围: {self.raw_data.iloc[0]['UTC_Time']} 到 {self.raw_data.iloc[-1]['UTC_Time']}")
            
            # 转换时间戳为datetime对象，确保timezone一致性
            self.raw_data['UTC_Time'] = pd.to_datetime(self.raw_data['UTC_Time'], errors='coerce')
            
            # 过滤掉无效的时间戳
            valid_time_mask = self.raw_data['UTC_Time'].notna()
            if not valid_time_mask.all():
                logger.warning(f"过滤掉 {len(valid_time_mask) - valid_time_mask.sum()} 条无效时间戳的记录")
            
            self.raw_data = self.raw_data[valid_time_mask]
            self.raw_data['UTC_Time'] = self.raw_data['UTC_Time'].dt.tz_localize(None)
            
            logger.info(f"有效记录数量: {len(self.raw_data)}")
            return True
            
        except FileNotFoundError:
            logger.error(f"找不到文件: {self.csv_file}")
            return False
        except pd.errors.EmptyDataError:
            logger.error("CSV文件为空")
            return False
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return False
    
    def load_btc_price_data(self):
        """从本地CSV文件加载比特币价格数据"""
        try:
            logger.info("从本地文件加载比特币价格数据...")
            
            self.btc_price_data = pd.read_csv(self.btc_price_file)
            
            # 检查必要的列
            if 'date' not in self.btc_price_data.columns or 'close_price' not in self.btc_price_data.columns:
                raise ValueError("BTC价格文件必须包含 'date' 和 'close_price' 列")
            
            # 转换日期格式
            self.btc_price_data['date'] = pd.to_datetime(self.btc_price_data['date'], errors='coerce')
            
            # 过滤无效数据
            valid_mask = self.btc_price_data['date'].notna() & self.btc_price_data['close_price'].notna()
            self.btc_price_data = self.btc_price_data[valid_mask]
            
            self.btc_price_data.set_index('date', inplace=True)
            
            # 只保留需要的列
            self.btc_price_data = self.btc_price_data[['close_price']].rename(columns={'close_price': 'close'})
            
            logger.info(f"成功加载 {len(self.btc_price_data)} 条BTC价格记录")
            logger.info(f"BTC价格范围: {self.btc_price_data['close'].min():.2f} - {self.btc_price_data['close'].max():.2f} USDT")
            
            return True
            
        except FileNotFoundError:
            logger.error(f"找不到BTC价格文件: {self.btc_price_file}")
            return False
        except Exception as e:
            logger.error(f"加载BTC价格数据失败: {e}")
            return False
    
    def analyze_transactions(self):
        """分析交易数据"""
        if self.raw_data is None:
            logger.error("请先加载数据")
            return False
        
        logger.info("开始分析交易数据...")
        
        # 加载BTC价格数据
        if not self.load_btc_price_data():
            logger.warning("无法加载BTC价格数据，将使用估算价格")
            self.btc_price_data = None
        
        # 按时间排序
        self.raw_data = self.raw_data.sort_values('UTC_Time')
        
        # 计算各资产的数量变化
        self._calculate_asset_balances()
        
        # 计算每日投资组合价值
        self._calculate_daily_portfolio_value()
        
        # 计算收益率
        self._calculate_returns()
        
        return True
    
    def _get_btc_price_for_date(self, date) -> float:
        """获取指定日期的BTC价格"""
        if self.btc_price_data is None or self.btc_price_data.empty:
            # 如果没有价格数据，使用基于时间的估算
            logger.warning(f"使用估算BTC价格 for {date}")
            # 简单的价格估算逻辑（基于大概的历史价格趋势）
            base_date = datetime(2021, 1, 1)
            days_diff = (date - base_date).days
            # 使用一个简单的指数增长模型作为估算
            return 30000 * (1.001 ** days_diff)  # 这个公式可以根据实际情况调整
        
        # 尝试获取精确日期的价格
        if date in self.btc_price_data.index:
            return float(self.btc_price_data.loc[date, 'close'])
        
        # 如果没有精确日期，使用最近的价格
        try:
            nearest_date = self.btc_price_data.index[
                self.btc_price_data.index.get_indexer([date], method='nearest')[0]
            ]
            return float(self.btc_price_data.loc[nearest_date, 'close'])
        except Exception as e:
            logger.warning(f"获取BTC价格失败 for {date}: {e}")
            return 95000.0  # 默认价格
    
    def _calculate_asset_balances(self):
        """计算各资产的数量变化"""
        logger.info("计算资产数量变化...")
        
        # 初始化资产余额（分开主账户和Spot Lead账户）
        self.asset_balances = {
            'USDT': 0.0,
            'BTC': 0.0,
            'BNB': 0.0,
            'ETH': 0.0,
            'SOL': 0.0,
            'BUSD': 0.0,
            'USD': 0.0
        }
        
        self.spot_lead_balances = {
            'USDT': 0.0,
            'BTC': 0.0,
            'BNB': 0.0,
            'ETH': 0.0,
            'SOL': 0.0,
            'BUSD': 0.0,
            'USD': 0.0
        }
        
        # 记录资产变化历史
        balance_history = []
        spot_lead_history = []
        
        # 遍历每笔交易
        for idx, row in self.raw_data.iterrows():
            account = row['Account']
            operation = row['Operation']
            coin = row['Coin']
            amount = float(row['Change'])
            remark = row['Remark']
            
            # 确定操作哪个账户的余额
            if account == 'Spot Lead':
                target_balances = self.spot_lead_balances
                target_history = spot_lead_history
            else:
                target_balances = self.asset_balances
                target_history = balance_history
            
            # 处理不同类型的交易
            if operation in ['Transaction Buy', 'Transaction Sold', 'Transaction Spend', 'Transaction Revenue']:
                if coin in target_balances:
                    target_balances[coin] += amount
            elif operation in ['Deposit', 'Withdraw', 'Send']:
                if coin in target_balances:
                    target_balances[coin] += amount
            elif operation in ['Copy Portfolio (Spot) - Profit Sharing with Leader']:
                # 带单收益分佣（USDT为正数）
                if coin in target_balances:
                    target_balances[coin] += amount
            elif operation in ['Lead Portfolio (Spot) - Create']:
                # 创建带单（USDT为负数）
                if coin in target_balances:
                    target_balances[coin] += amount
            elif operation in ['Lead Portfolio (Spot) - Deposit', 'Lead Portfolio (Spot) - Withdraw']:
                # 带单资金转移
                if coin in target_balances:
                    target_balances[coin] += amount
            
            # 记录余额变化
            balance_copy = target_balances.copy()
            balance_copy['timestamp'] = row['UTC_Time']
            balance_copy['operation'] = operation
            balance_copy['coin'] = coin
            balance_copy['amount'] = amount
            balance_copy['remark'] = remark
            balance_copy['account'] = account
            target_history.append(balance_copy)
        
        self.balance_history = pd.DataFrame(balance_history)
        self.spot_lead_history = pd.DataFrame(spot_lead_history)
        logger.info("资产数量变化计算完成")
        
        # 打印最终余额
        logger.info("=== 主账户最终资产余额 ===")
        for asset, balance in self.asset_balances.items():
            if abs(balance) > 1e-8:  # 只显示非零余额
                logger.info(f"{asset}: {balance:.8f}")
        
        logger.info("=== Spot Lead账户最终资产余额 ===")
        for asset, balance in self.spot_lead_balances.items():
            if abs(balance) > 1e-8:  # 只显示非零余额
                logger.info(f"{asset}: {balance:.8f}")
    
    def _calculate_daily_portfolio_value(self):
        """计算每日投资组合价值"""
        logger.info("计算每日投资组合价值...")
        
        if self.balance_history.empty and self.spot_lead_history.empty:
            logger.error("没有余额历史数据")
            return
        
        # 创建日期范围
        all_timestamps = pd.concat([
            self.balance_history['timestamp'] if not self.balance_history.empty else pd.Series(),
            self.spot_lead_history['timestamp'] if not self.spot_lead_history.empty else pd.Series()
        ])
        
        if all_timestamps.empty:
            logger.error("没有有效的时间戳数据")
            return
        
        start_date = all_timestamps.min().date()
        end_date = all_timestamps.max().date()
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 初始化每日价值
        daily_values = []
        
        # 合并主账户和Spot Lead账户的余额
        def get_balances_at_time(timestamp):
            """获取指定时间的资产余额"""
            # 获取主账户余额
            main_balance = {}
            if not self.balance_history.empty:
                main_history_up_to_time = self.balance_history[self.balance_history['timestamp'] <= timestamp]
                if not main_history_up_to_time.empty:
                    main_balance = main_history_up_to_time.iloc[-1].to_dict()
                    # 提取资产余额
                    main_balance = {k: v for k, v in main_balance.items() if k in ['USDT', 'BTC', 'BNB', 'ETH', 'SOL', 'BUSD', 'USD']}
            
            # 获取Spot Lead账户余额
            spot_lead_balance = {}
            if not self.spot_lead_history.empty:
                spot_history_up_to_time = self.spot_lead_history[self.spot_lead_history['timestamp'] <= timestamp]
                if not spot_history_up_to_time.empty:
                    spot_balance = spot_history_up_to_time.iloc[-1].to_dict()
                    spot_lead_balance = {k: v for k, v in spot_balance.items() if k in ['USDT', 'BTC', 'BNB', 'ETH', 'SOL', 'BUSD', 'USD']}
            
            # 合并余额（只包含非负值）
            combined_balance = {}
            all_assets = set(list(main_balance.keys()) + list(spot_lead_balance.keys()))
            
            for asset in all_assets:
                main_val = main_balance.get(asset, 0.0)
                spot_val = spot_lead_balance.get(asset, 0.0)
                # 确保余额不为负
                combined_balance[asset] = max(0.0, main_val) + max(0.0, spot_val)
            
            return combined_balance
        
        # 遍历每个日期
        for date in date_range:
            end_of_day = pd.Timestamp(date) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            
            # 获取当日结束时的余额
            balances = get_balances_at_time(end_of_day)
            
            if balances:
                portfolio_value = 0.0
                
                # 计算总价值
                for asset, balance in balances.items():
                    if asset == 'USDT' or asset == 'USD':
                        portfolio_value += balance
                    elif asset == 'BTC':
                        # 使用从文件获取的BTC价格
                        btc_price = self._get_btc_price_for_date(date)
                        portfolio_value += balance * btc_price
                    else:
                        # 其他资产使用估算价格
                        price = self._get_price_estimate(asset, date)
                        portfolio_value += balance * price
                
                daily_values.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'USDT_balance': balances.get('USDT', 0.0),
                    'BTC_balance': balances.get('BTC', 0.0),
                    'BTC_price': self._get_btc_price_for_date(date),
                    'ETH_balance': balances.get('ETH', 0.0),
                    'BNB_balance': balances.get('BNB', 0.0),
                    'SOL_balance': balances.get('SOL', 0.0),
                    'other_balance': sum(v for k, v in balances.items() if k not in ['USDT', 'BTC', 'ETH', 'BNB', 'SOL', 'USD'])
                })
        
        self.daily_portfolio_value = pd.DataFrame(daily_values)
        logger.info(f"计算了 {len(self.daily_portfolio_value)} 天的投资组合价值")
        
        # 打印价格信息
        if not self.daily_portfolio_value.empty:
            btc_prices = self.daily_portfolio_value['BTC_price']
            portfolio_values = self.daily_portfolio_value['portfolio_value']
            logger.info(f"BTC价格范围: {btc_prices.min():.2f} - {btc_prices.max():.2f} USDT")
            logger.info(f"投资组合价值范围: {portfolio_values.min():.2f} - {portfolio_values.max():.2f} USDT")
    
    def _get_price_estimate(self, coin: str, date) -> float:
        """获取资产价格估算（用于非BTC资产）"""
        # 更详细的价格估算表
        price_estimates = {
            'USDT': 1.0,
            'BUSD': 1.0,
            'USD': 1.0,
            'ETH': 3000.0,
            'BNB': 300.0,
            'SOL': 100.0,
            'ADA': 0.5,
            'DOT': 10.0,
            'LINK': 15.0,
            'AVAX': 30.0,
            'UNI': 6.0,
            'ATOM': 10.0,
            'MATIC': 0.5,
            'XRP': 0.5,
            'LTC': 70.0,
            'BCH': 250.0,
            'DOGE': 0.08
        }
        return price_estimates.get(coin, 1.0)
    
    def _calculate_returns(self):
        """计算收益率"""
        if self.daily_portfolio_value is None or self.daily_portfolio_value.empty:
            logger.error("没有投资组合价值数据")
            return
        
        logger.info("计算收益率...")
        
        # 计算日收益率
        self.daily_portfolio_value['daily_return'] = self.daily_portfolio_value['portfolio_value'].pct_change()
        
        # 计算累计收益率
        initial_value = self.daily_portfolio_value['portfolio_value'].iloc[0]
        if initial_value > 0:
            self.daily_portfolio_value['cumulative_return'] = (
                self.daily_portfolio_value['portfolio_value'] - initial_value
            ) / initial_value
        
        # 计算统计指标
        self.return_stats = {
            'total_return': (self.daily_portfolio_value['portfolio_value'].iloc[-1] - initial_value) / initial_value if initial_value > 0 else 0,
            'annualized_return': None,
            'volatility': self.daily_portfolio_value['daily_return'].std(),
            'max_drawdown': None,
            'sharpe_ratio': None,
            'total_days': len(self.daily_portfolio_value),
            'positive_days': len(self.daily_portfolio_value[self.daily_portfolio_value['daily_return'] > 0]),
            'negative_days': len(self.daily_portfolio_value[self.daily_portfolio_value['daily_return'] < 0])
        }
        
        # 计算年化收益率
        days = self.return_stats['total_days']
        if days > 0:
            years = days / 365.25
            if years > 0:
                self.return_stats['annualized_return'] = (1 + self.return_stats['total_return']) ** (1 / years) - 1
        
        # 计算最大回撤
        peak = self.daily_portfolio_value['portfolio_value'].expanding().max()
        drawdown = (self.daily_portfolio_value['portfolio_value'] - peak) / peak
        self.return_stats['max_drawdown'] = drawdown.min()
        
        # 计算夏普比率（假设无风险利率为2%）
        risk_free_rate = 0.02  # 2%年化无风险利率
        daily_risk_free = (1 + risk_free_rate) ** (1 / 365.25) - 1
        excess_returns = self.daily_portfolio_value['daily_return'] - daily_risk_free
        
        if self.return_stats['volatility'] > 0:
            self.return_stats['sharpe_ratio'] = excess_returns.mean() / self.return_stats['volatility'] * np.sqrt(365.25)
        
        logger.info("收益率计算完成")
    
    def _generate_transactions_pyfolio(self):
        """生成transactions数据（pyfolio格式）"""
        logger.info("生成transactions数据...")
        
        transactions = []
        
        # 根据README：只记录交易比特币的数据
        # 需要匹配的BTC交易操作和对应的USDT交易操作
        valid_operations = ['Transaction Buy', 'Transaction Sold', 'Transaction Spend', 'Transaction Revenue']
        
        # 从原始交易数据中提取BTC交易
        for _, row in self.raw_data.iterrows():
            date = row['UTC_Time'].date()
            operation = row['Operation']
            coin = row['Coin']
            amount = float(row['Change'])
            account = row['Account']
            
            # 跳过Spot Lead账户和无效的操作/币种
            if account == 'Spot Lead' or operation not in valid_operations:
                continue
            
            try:
                # 根据README的最新解释：
                # 只记录交易比特币的数据
                # txn_volume: 交易比特币的USDT金额，买入时为正，txn_volume = - Transaction Spend USDT change，卖出时为负，txn_volume = - Transaction Revenue USDT change
                # txn_shares: 交易比特币的数量，买入时为正，txn_shares = Transaction Buy BTC change，卖出时为负，txn_shares = Transaction Sold BTC change
                
                if coin == 'BTC':
                    # 处理BTC交易记录
                    if operation == 'Transaction Buy':
                        # 买入BTC：amount是正数，表示买入的BTC数量
                        txn_shares = amount  # 买入BTC数量（正数）
                        # 需要找到对应的Transaction Spend USDT记录来计算txn_volume
                        txn_volume = self._find_matching_usdt_spend(date, amount)
                    elif operation == 'Transaction Sold':
                        # 卖出BTC：amount是正数，表示卖出的BTC数量
                        txn_shares = -amount  # 卖出BTC数量（负数）
                        # 需要找到对应的Transaction Revenue USDT记录来计算txn_volume
                        txn_volume = self._find_matching_usdt_revenue(date, amount)
                    else:
                        # BTC不应该有Spend/Revenue操作，跳过
                        continue
                        
                    # 只记录有效交易（排除零值）
                    if abs(txn_shares) > 1e-10 and abs(txn_volume) > 1e-10:
                        transactions.append({
                            'date': date,
                            'txn_shares': txn_shares,
                            'txn_volume': txn_volume
                        })
                        
                # USDT记录用于匹配BTC交易，不直接记录到transactions中
                # 但我们需要收集这些信息用于匹配
                
            except Exception as e:
                logger.warning(f"处理交易失败 {date} {operation} {coin} {amount}: {e}")
                continue
        
        # 如果没有找到匹配的交易，尝试从USDT记录反推BTC交易
        if not transactions:
            logger.info("没有找到BTC交易记录，尝试从USDT记录反推...")
            transactions = self._generate_transactions_from_usdt()
        
        # 转换为DataFrame并按日期排序
        if transactions:
            transactions_df = pd.DataFrame(transactions)
            # 按日期分组，计算每日的总交易
            transactions_df = transactions_df.groupby('date').agg({
                'txn_volume': 'sum',
                'txn_shares': 'sum'
            }).reset_index()
            
            # 确保日期列存在
            if 'date' not in transactions_df.columns:
                transactions_df['date'] = pd.to_datetime(transactions_df['date']).dt.date
            
            transactions_df.set_index('date', inplace=True)
            
            # 保存到CSV（只保留README要求的列：date, txn_volume, txn_shares）
            transactions_pyfolio = transactions_df[['txn_volume', 'txn_shares']].copy()
            transactions_pyfolio.to_csv('transactions_pyfolio.csv')
            logger.info(f"transactions数据已保存到 transactions_pyfolio.csv，共 {len(transactions_pyfolio)} 条记录")
            
            # 打印交易统计
            logger.info("=== 交易统计 ===")
            total_volume = transactions_df['txn_volume'].sum()
            total_shares = transactions_df['txn_shares'].sum()
            logger.info(f"BTC交易: {len(transactions_df)} 笔交易, "
                       f"总成交量: {total_volume:.2f}, "
                       f"总成交股数: {total_shares:.8f}")
        else:
            # 创建空文件
            pd.DataFrame(columns=['date', 'txn_volume', 'txn_shares']).to_csv('transactions_pyfolio.csv', index=False)
            logger.info("没有有效交易，创建空的transactions_pyfolio.csv")
    
    def _find_matching_usdt_spend(self, date, btc_amount):
        """找到匹配的USDT Transaction Spend记录"""
        # 获取同一天的USDT Transaction Spend记录
        same_day_usdt = self.raw_data[
            (self.raw_data['UTC_Time'].dt.date == date) &
            (self.raw_data['Coin'] == 'USDT') &
            (self.raw_data['Operation'] == 'Transaction Spend') &
            (self.raw_data['Account'] != 'Spot Lead')
        ]
        
        if not same_day_usdt.empty:
            # 使用第一条记录的金额
            usdt_amount = same_day_usdt.iloc[0]['Change']
            # 根据README：买入时为正，txn_volume = - Transaction Spend USDT change
            return -usdt_amount
        else:
            # 如果没找到，使用BTC价格估算
            btc_price = self._get_btc_price_for_date(date)
            return btc_amount * btc_price
    
    def _find_matching_usdt_revenue(self, date, btc_amount):
        """找到匹配的USDT Transaction Revenue记录"""
        # 获取同一天的USDT Transaction Revenue记录
        same_day_usdt = self.raw_data[
            (self.raw_data['UTC_Time'].dt.date == date) &
            (self.raw_data['Coin'] == 'USDT') &
            (self.raw_data['Operation'] == 'Transaction Revenue') &
            (self.raw_data['Account'] != 'Spot Lead')
        ]
        
        if not same_day_usdt.empty:
            # 使用第一条记录的金额
            usdt_amount = same_day_usdt.iloc[0]['Change']
            # 根据README：卖出时为负，txn_volume = - Transaction Revenue USDT change
            return -usdt_amount
        else:
            # 如果没找到，使用BTC价格估算
            btc_price = self._get_btc_price_for_date(date)
            return -btc_amount * btc_price
    
    def _generate_transactions_from_usdt(self):
        """从USDT记录反推BTC交易"""
        transactions = []
        
        # 获取所有USDT交易记录
        usdt_transactions = self.raw_data[
            (self.raw_data['Coin'] == 'USDT') &
            (self.raw_data['Operation'].isin(['Transaction Spend', 'Transaction Revenue'])) &
            (self.raw_data['Account'] != 'Spot Lead')
        ].copy()
        
        # 按日期分组处理
        for date, group in usdt_transactions.groupby(usdt_transactions['UTC_Time'].dt.date):
            for _, row in group.iterrows():
                operation = row['Operation']
                usdt_amount = row['Change']
                
                try:
                    if operation == 'Transaction Spend':
                        # 买入花费，txn_volume = - Transaction Spend USDT change (正数)
                        txn_volume = -usdt_amount
                        # 使用价格估算BTC数量
                        btc_price = self._get_btc_price_for_date(date)
                        txn_shares = txn_volume / btc_price if btc_price > 0 else 0
                    elif operation == 'Transaction Revenue':
                        # 卖出收入，txn_volume = - Transaction Revenue USDT change (负数)
                        txn_volume = -usdt_amount
                        # 使用价格估算BTC数量
                        btc_price = self._get_btc_price_for_date(date)
                        txn_shares = txn_volume / btc_price if btc_price > 0 else 0
                    else:
                        continue
                    
                    # 只记录有效交易
                    if abs(txn_shares) > 1e-10 and abs(txn_volume) > 1e-10:
                        transactions.append({
                            'date': date,
                            'txn_shares': txn_shares,
                            'txn_volume': txn_volume
                        })
                        
                except Exception as e:
                    logger.warning(f"处理USDT交易失败 {date} {operation} {usdt_amount}: {e}")
                    continue
        
        return transactions
    
    def _generate_positions_pyfolio(self):
        """生成positions数据（pyfolio格式）"""
        logger.info("生成positions数据...")
        
        positions = []
        
        # 按日期计算持仓
        for _, row in self.daily_portfolio_value.iterrows():
            date = row['date']
            
            # 计算各资产的价值
            pos_data = {
                'date': date,
                'USDT': row['USDT_balance'],
                'USD': row.get('other_balance', 0.0),  # 将其他稳定币合并到USD
                'cash': row['USDT_balance'] + row.get('other_balance', 0.0),  # 现金以USDT计
                'BTC': row['BTC_balance'] * row['BTC_price']
            }
            
            # 添加其他资产价值
            eth_price = self._get_price_estimate('ETH', date)
            bnb_price = self._get_price_estimate('BNB', date)
            sol_price = self._get_price_estimate('SOL', date)
            
            pos_data['ETH'] = row.get('ETH_balance', 0.0) * eth_price
            pos_data['BNB'] = row.get('BNB_balance', 0.0) * bnb_price
            pos_data['SOL'] = row.get('SOL_balance', 0.0) * sol_price
            
            positions.append(pos_data)
        
        # 转换为DataFrame并按日期排序
        positions_df = pd.DataFrame(positions)
        if not positions_df.empty:
            positions_df = positions_df.sort_values('date')
            positions_df.set_index('date', inplace=True)
            # 确保数值列都是正数
            for col in ['USDT', 'USD', 'cash', 'BTC', 'ETH', 'BNB', 'SOL']:
                if col in positions_df.columns:
                    positions_df[col] = positions_df[col].abs()
            
            # 保存到CSV（只保留README要求的列：date, BTC, cash）
            positions_pyfolio = positions_df[['BTC', 'cash']].copy()
            positions_pyfolio.to_csv('positions_pyfolio.csv')
            logger.info(f"positions数据已保存到 positions_pyfolio.csv，共 {len(positions_pyfolio)} 条记录")
            
            # 打印持仓统计
            logger.info("=== 持仓统计 ===")
            total_value = positions_df.iloc[-1].sum()
            for col in ['USDT', 'USD', 'cash', 'BTC', 'ETH', 'BNB', 'SOL']:
                if col in positions_df.columns:
                    value = positions_df[col].iloc[-1]
                    if value > 0:
                        pct = (value / total_value) * 100 if total_value > 0 else 0
                        logger.info(f"{col}: {value:.2f} USDT ({pct:.1f}%)")
        else:
            # 创建空文件
            pd.DataFrame(columns=['date', 'USDT', 'USD', 'cash', 'BTC', 'ETH', 'BNB', 'SOL']).to_csv('positions_pyfolio.csv', index=False)
            logger.info("没有持仓数据，创建空的positions_pyfolio.csv")
    
    def _generate_returns_pyfolio(self):
        """生成returns数据（pyfolio格式）"""
        logger.info("生成returns数据...")
        
        # 准备returns数据
        if self.daily_portfolio_value is None or self.daily_portfolio_value.empty:
            logger.warning("没有投资组合价值数据，创建空returns文件")
            pd.DataFrame(columns=['returns']).to_csv('returns_pyfolio.csv', index=False)
            return
        
        returns_df = self.daily_portfolio_value[['date', 'daily_return']].copy()
        returns_df = returns_df.rename(columns={'daily_return': 'returns'})
        returns_df = returns_df.dropna(subset=['returns'])  # 删除第一天的NaN
        
        if not returns_df.empty:
            returns_df['date'] = pd.to_datetime(returns_df['date']).dt.date
            returns_df.set_index('date', inplace=True)
            returns_df.to_csv('returns_pyfolio.csv')
            logger.info(f"returns数据已保存到 returns_pyfolio.csv，共 {len(returns_df)} 条记录")
            
            # 打印收益统计
            logger.info("=== 收益统计 ===")
            logger.info(f"平均日收益率: {returns_df['returns'].mean():.4f}")
            logger.info(f"收益率标准差: {returns_df['returns'].std():.4f}")
            logger.info(f"最大日收益率: {returns_df['returns'].max():.4f}")
            logger.info(f"最小日收益率: {returns_df['returns'].min():.4f}")
            
            # 计算收益分布
            positive_count = (returns_df['returns'] > 0).sum()
            negative_count = (returns_df['returns'] < 0).sum()
            zero_count = (returns_df['returns'] == 0).sum()
            
            logger.info(f"盈利天数: {positive_count} ({positive_count/len(returns_df)*100:.1f}%)")
            logger.info(f"亏损天数: {negative_count} ({negative_count/len(returns_df)*100:.1f}%)")
            logger.info(f"持平天数: {zero_count} ({zero_count/len(returns_df)*100:.1f}%)")
        else:
            logger.info("没有收益数据")
    
    def generate_pyfolio_data(self):
        """生成pyfolio格式的数据"""
        if self.daily_portfolio_value is None or self.daily_portfolio_value.empty:
            logger.error("没有投资组合价值数据")
            return
        
        logger.info("生成pyfolio格式数据...")
        
        # 1. 生成transactions数据
        self._generate_transactions_pyfolio()
        
        # 2. 生成positions数据
        self._generate_positions_pyfolio()
        
        # 3. 生成returns数据
        self._generate_returns_pyfolio()
        
        logger.info("pyfolio格式数据生成完成")
        
        # 验证生成的文件
        self._validate_pyfolio_files()
    
    def _validate_pyfolio_files(self):
        """验证pyfolio文件的格式"""
        logger.info("验证pyfolio文件格式...")
        
        try:
            # 验证transactions文件
            transactions_df = pd.read_csv('transactions_pyfolio.csv')
            required_tx_columns = ['txn_volume', 'txn_shares']  # README要求的列
            missing_tx_columns = [col for col in required_tx_columns if col not in transactions_df.columns]
            if missing_tx_columns:
                logger.warning(f"transactions文件缺少列: {missing_tx_columns}")
            else:
                logger.info("transactions文件格式正确")
            
            # 验证positions文件
            positions_df = pd.read_csv('positions_pyfolio.csv')
            required_pos_columns = ['date', 'cash']  # 至少需要这些基本列
            missing_pos_columns = [col for col in required_pos_columns if col not in positions_df.columns]
            if missing_pos_columns:
                logger.warning(f"positions文件缺少列: {missing_pos_columns}")
            else:
                logger.info("positions文件格式正确")
            
            # 验证returns文件
            returns_df = pd.read_csv('returns_pyfolio.csv')
            required_ret_columns = ['returns']
            missing_ret_columns = [col for col in required_ret_columns if col not in returns_df.columns]
            if missing_ret_columns:
                logger.warning(f"returns文件缺少列: {missing_ret_columns}")
            else:
                logger.info("returns文件格式正确")
                
        except Exception as e:
            logger.error(f"验证pyfolio文件失败: {e}")
    
    def generate_report(self):
        """生成分析报告"""
        if not hasattr(self, 'return_stats'):
            logger.error("请先运行分析")
            return
        
        logger.info("=== 币安交易记录分析报告 ===")
        
        # 基本统计
        logger.info("\n=== 基本统计 ===")
        logger.info(f"交易记录总数: {len(self.raw_data)}")
        logger.info(f"分析时间范围: {self.raw_data.iloc[0]['UTC_Time']} 到 {self.raw_data.iloc[-1]['UTC_Time']}")
        logger.info(f"分析天数: {self.return_stats['total_days']}")
        
        # 价格数据信息
        if self.btc_price_data is not None and not self.btc_price_data.empty:
            logger.info(f"BTC价格数据: {len(self.btc_price_data)} 条记录")
            logger.info(f"BTC价格范围: {self.btc_price_data['close'].min():.2f} - {self.btc_price_data['close'].max():.2f} USDT")
        else:
            logger.info("BTC价格数据: 使用估算价格")
        
        # 收益率统计
        logger.info("\n=== 收益率统计 ===")
        logger.info(f"总收益率: {self.return_stats['total_return']:.2%}")
        if self.return_stats['annualized_return'] is not None:
            logger.info(f"年化收益率: {self.return_stats['annualized_return']:.2%}")
        logger.info(f"波动率: {self.return_stats['volatility']:.2%}")
        logger.info(f"最大回撤: {self.return_stats['max_drawdown']:.2%}")
        if self.return_stats['sharpe_ratio'] is not None:
            logger.info(f"夏普比率: {self.return_stats['sharpe_ratio']:.2f}")
        logger.info(f"盈利天数: {self.return_stats['positive_days']}")
        logger.info(f"亏损天数: {self.return_stats['negative_days']}")
        if self.return_stats['total_days'] > 0:
            logger.info(f"胜率: {self.return_stats['positive_days']/self.return_stats['total_days']:.1%}")
        
        # 资产余额
        logger.info("\n=== 主账户最终资产余额 ===")
        total_value_usdt = 0.0
        for asset, balance in self.asset_balances.items():
            if abs(balance) > 1e-8:
                if asset == 'USDT':
                    value_usdt = balance
                elif asset == 'BTC':
                    current_btc_price = self._get_btc_price_for_date(datetime.now().date())
                    value_usdt = balance * current_btc_price
                else:
                    value_usdt = balance * self._get_price_estimate(asset, datetime.now().date())
                
                logger.info(f"{asset}: {balance:.8f} (约 {value_usdt:.2f} USDT)")
                total_value_usdt += value_usdt
        
        logger.info(f"主账户总资产价值: {total_value_usdt:.2f} USDT")
        
        # Spot Lead账户余额
        logger.info("\n=== Spot Lead账户最终资产余额 ===")
        spot_lead_total_value = 0.0
        for asset, balance in self.spot_lead_balances.items():
            if abs(balance) > 1e-8:
                if asset == 'USDT':
                    value_usdt = balance
                elif asset == 'BTC':
                    current_btc_price = self._get_btc_price_for_date(datetime.now().date())
                    value_usdt = balance * current_btc_price
                else:
                    value_usdt = balance * self._get_price_estimate(asset, datetime.now().date())
                
                logger.info(f"{asset}: {balance:.8f} (约 {value_usdt:.2f} USDT)")
                spot_lead_total_value += value_usdt
        
        logger.info(f"Spot Lead账户总资产价值: {spot_lead_total_value:.2f} USDT")
        logger.info(f"两个账户总价值: {total_value_usdt + spot_lead_total_value:.2f} USDT")
        
        # 交易类型分析
        logger.info("\n=== 交易类型分析 ===")
        operation_counts = self.raw_data['Operation'].value_counts()
        for operation, count in operation_counts.items():
            logger.info(f"{operation}: {count}")
        
        # 账户分析
        logger.info("\n=== 账户分析 ===")
        account_counts = self.raw_data['Account'].value_counts()
        for account, count in account_counts.items():
            logger.info(f"{account}: {count} 笔交易")
        
        # 币单收益分析
        copy_trade_data = self.raw_data[self.raw_data['Operation'].str.contains('Copy Portfolio', na=False)]
        if not copy_trade_data.empty:
            copy_profit = copy_trade_data[copy_trade_data['Operation'].str.contains('Profit Sharing', na=False)]
            if not copy_profit.empty:
                total_copy_profit = copy_profit['Change'].sum()
                logger.info(f"\n=== 币单收益 ===")
                logger.info(f"总带单收益: {total_copy_profit:.2f} USDT")
                logger.info(f"带单收益笔数: {len(copy_profit)}")
        
        # 期货交易分析
        futures_data = self.raw_data[self.raw_data['Account'] == 'USD-M Futures']
        if not futures_data.empty:
            funding_fees = futures_data[futures_data['Operation'] == 'Funding Fee']
            if not funding_fees.empty:
                total_funding_fee = funding_fees['Change'].sum()
                pnl_trades = futures_data[futures_data['Operation'] == 'Realized Profit and Loss']
                total_pnl = pnl_trades['Change'].sum() if not pnl_trades.empty else 0
                
                logger.info(f"\n=== 期货交易 ===")
                logger.info(f"总资金费用: {total_funding_fee:.2f} USDT")
                logger.info(f"总已实现盈亏: {total_pnl:.2f} USDT")
                logger.info(f"资金费用笔数: {len(funding_fees)}")
                logger.info(f"已实现盈亏笔数: {len(pnl_trades)}")
    
    def save_results(self):
        """保存分析结果"""
        if self.daily_portfolio_value is not None:
            # 保存投资组合价值数据（包含BTC价格）
            self.daily_portfolio_value.to_csv('portfolio_value_with_prices.csv', index=False)
            logger.info("投资组合价值数据已保存到 portfolio_value_with_prices.csv")
        
        # 保存资产余额
        balance_data = []
        for asset, balance in self.asset_balances.items():
            balance_data.append({'Asset': asset, 'Balance': balance, 'Account': 'Main'})
        
        for asset, balance in self.spot_lead_balances.items():
            balance_data.append({'Asset': asset, 'Balance': balance, 'Account': 'Spot Lead'})
        
        balance_df = pd.DataFrame(balance_data)
        balance_df.to_csv('final_balances.csv', index=False)
        logger.info("最终资产余额已保存到 final_balances.csv")
        
        # 保存BTC价格数据
        if self.btc_price_data is not None and not self.btc_price_data.empty:
            self.btc_price_data.to_csv('btc_price_data.csv')
            logger.info("BTC价格数据已保存到 btc_price_data.csv")
        
        # 保存详细的分析结果
        if hasattr(self, 'return_stats'):
            stats_df = pd.DataFrame([self.return_stats])
            stats_df.to_csv('return_statistics.csv', index=False)
            logger.info("收益率统计已保存到 return_statistics.csv")
    
    def plot_results(self):
        """生成可视化图表"""
        try:
            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(3, 2, figsize=(18, 15))
            
            if self.daily_portfolio_value is None or self.daily_portfolio_value.empty:
                logger.warning("没有投资组合价值数据，跳过图表生成")
                return
            
            # 投资组合价值变化
            ax1 = axes[0, 0]
            ax1.plot(self.daily_portfolio_value['date'], self.daily_portfolio_value['portfolio_value'], 
                    label='Portfolio Value', color='blue')
            ax1.set_title('Portfolio Value Change')
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Value (USDT)')
            ax1.grid(True)
            ax1.legend()
            
            # BTC价格变化
            ax2 = axes[0, 1]
            ax2.plot(self.daily_portfolio_value['date'], self.daily_portfolio_value['BTC_price'], 
                    label='BTC Price', color='orange')
            ax2.set_title('BTC Price Change')
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Price (USDT)')
            ax2.grid(True)
            ax2.legend()
            
            # 日收益率分布
            ax3 = axes[1, 0]
            ax3.hist(self.daily_portfolio_value['daily_return'].dropna(), bins=50, color='green', alpha=0.7)
            ax3.set_title('Daily Return Distribution')
            ax3.set_xlabel('Return')
            ax3.set_ylabel('Frequency')
            ax3.grid(True)
            
            # 累计收益率
            ax4 = axes[1, 1]
            if 'cumulative_return' in self.daily_portfolio_value.columns:
                ax4.plot(self.daily_portfolio_value['date'], self.daily_portfolio_value['cumulative_return'] * 100, 
                        label='Cumulative Return', color='red')
                ax4.set_title('Cumulative Return')
                ax4.set_xlabel('Date')
                ax4.set_ylabel('Return (%)')
                ax4.grid(True)
                ax4.legend()
            else:
                ax4.text(0.5, 0.5, 'No cumulative return data', ha='center', va='center', transform=ax4.transAxes)
                ax4.set_title('Cumulative Return (No Data)')
            
            # 投资组合价值 vs BTC价格
            ax5 = axes[2, 0]
            ax5.plot(self.daily_portfolio_value['date'], self.daily_portfolio_value['portfolio_value'], 
                    'b-', label='Portfolio Value', color='blue')
            ax5.plot(self.daily_portfolio_value['date'], 
                    self.daily_portfolio_value['portfolio_value'] / self.daily_portfolio_value['BTC_price'], 
                    'r--', label='Portfolio/BTC Ratio', color='purple')
            ax5.set_title('Portfolio Value vs BTC Price')
            ax5.set_xlabel('Date')
            ax5.set_ylabel('Value (USDT)')
            ax5.grid(True)
            ax5.legend()
            
            # Asset Allocation (Pie Chart)
            ax6 = axes[2, 1]
            asset_values = []
            asset_names = []
            
            # Calculate current value of each asset for both accounts
            current_date = self.daily_portfolio_value['date'].iloc[-1]
            current_btc_price = self._get_btc_price_for_date(current_date)
            
            # 合并两个账户的资产
            combined_balances = self.asset_balances.copy()
            for asset, balance in self.spot_lead_balances.items():
                combined_balances[asset] = combined_balances.get(asset, 0.0) + balance
            
            for asset, balance in combined_balances.items():
                if abs(balance) > 1e-8:
                    if asset == 'USDT':
                        value = balance
                    elif asset == 'BTC':
                        value = balance * current_btc_price
                    else:
                        value = balance * self._get_price_estimate(asset, current_date)
                    
                    if value > 0:
                        asset_values.append(value)
                        asset_names.append(f"{asset}\n({value:.0f} USDT)")
            
            if asset_values:
                ax6.pie(asset_values, labels=asset_names, autopct='%1.1f%%')
                ax6.set_title('Asset Allocation (Combined Accounts)')
            
            plt.tight_layout()
            plt.savefig('portfolio_analysis_enhanced.png', dpi=300, bbox_inches='tight')
            plt.show()
            logger.info("图表已保存到 portfolio_analysis_enhanced.png")
            
        except Exception as e:
            logger.error(f"生成图表失败: {e}")

def main():
    """主函数"""
    # 使用您提供的交易记录文件
    csv_file = "58f7aff0-e0a5-11f0-a3f8-069f3b29e123-1.csv"
    
    # 创建分析器
    analyzer = BinanceTransactionAnalyzer(csv_file)
    
    # 加载数据
    if analyzer.load_data():
        # 分析数据
        if analyzer.analyze_transactions():
            # 生成报告
            analyzer.generate_report()
            
            # 生成pyfolio格式数据
            analyzer.generate_pyfolio_data()
            
            # 保存结果
            analyzer.save_results()
            
            # 生成图表
            analyzer.plot_results()
            
            logger.info("\n分析完成！")
        else:
            logger.error("数据分析失败")
    else:
        logger.error("数据加载失败")

if __name__ == "__main__":
    main()
