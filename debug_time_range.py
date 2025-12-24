#!/usr/bin/env python3
"""
调试时间范围和数据获取问题
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import ccxt
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_time_range_and_data():
    """调试时间范围和数据获取"""
    
    # 加载环境变量
    load_dotenv()
    
    # 初始化交易所
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key or not secret_key:
        logger.error("❌ 未找到主账户API密钥")
        return
    
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret_key,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
        },
    })
    
    try:
        # 测试连接
        logger.info("🔍 测试API连接...")
        balance = exchange.fetch_balance()
        logger.info("✅ API连接成功")
        
        # 获取所有充值记录
        logger.info("🔍 获取所有充值记录...")
        all_deposits = []
        since = None
        more_data = True
        
        while more_data:
            try:
                deposits = exchange.fetch_deposits(
                    since=since, 
                    limit=1000
                )
                
                if deposits:
                    logger.info(f"   获取到 {len(deposits)} 条充值记录")
                    # 过滤USDT记录
                    usdt_deposits = [d for d in deposits if d['currency'] == 'USDT']
                    all_deposits.extend(usdt_deposits)
                    logger.info(f"   其中USDT记录: {len(usdt_deposits)} 条")
                    # 更新since为最后一条记录的时间
                    since = deposits[-1]['timestamp'] + 1
                else:
                    more_data = False
                    
            except Exception as e:
                logger.error(f"   获取充值记录时出错: {e}")
                break
        
        # 获取所有提现记录
        logger.info("🔍 获取所有提现记录...")
        all_withdrawals = []
        since = None
        more_data = True
        
        while more_data:
            try:
                withdrawals = exchange.fetch_withdrawals(
                    since=since, 
                    limit=1000
                )
                
                if withdrawals:
                    logger.info(f"   获取到 {len(withdrawals)} 条提现记录")
                    # 过滤USDT记录
                    usdt_withdrawals = [w for w in withdrawals if w['currency'] == 'USDT']
                    all_withdrawals.extend(usdt_withdrawals)
                    logger.info(f"   其中USDT记录: {len(usdt_withdrawals)} 条")
                    # 更新since为最后一条记录的时间
                    since = withdrawals[-1]['timestamp'] + 1
                else:
                    more_data = False
                    
            except Exception as e:
                logger.error(f"   获取提现记录时出错: {e}")
                break
        
        logger.info(f"📊 总计获取到:")
        logger.info(f"   USDT充值记录: {len(all_deposits)} 条")
        logger.info(f"   USDT提现记录: {len(all_withdrawals)} 条")
        
        # 显示详细记录
        if all_deposits:
            logger.info("💰 USDT充值记录详情:")
            for deposit in all_deposits[:5]:  # 只显示前5条
                tx_time = pd.to_datetime(deposit['timestamp'], unit='ms')
                amount = deposit['amount']
                status = deposit['status']
                logger.info(f"   {tx_time}: +{amount} USDT (状态: {status})")
        
        if all_withdrawals:
            logger.info("💸 USDT提现记录详情:")
            for withdrawal in all_withdrawals[:5]:  # 只显示前5条
                tx_time = pd.to_datetime(withdrawal['timestamp'], unit='ms')
                amount = withdrawal['amount']
                status = withdrawal['status']
                logger.info(f"   {tx_time}: -{amount} USDT (状态: {status})")
        
        # 获取交易记录
        logger.info("🔍 获取BTC/USDT交易记录...")
        copytrade_api_key = os.getenv('BINANCE_COPYTRADE_API_KEY')
        copytrade_secret_key = os.getenv('BINANCE_COPYTRADE_SECRET_KEY')
        
        if copytrade_api_key and copytrade_secret_key:
            copytrade_exchange = ccxt.binance({
                'apiKey': copytrade_api_key,
                'secret': copytrade_secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                },
            })
            
            all_trades = []
            since = None
            more_data = True
            
            while more_data:
                try:
                    trades = copytrade_exchange.fetch_my_trades(
                        symbol='BTC/USDT', 
                        since=since, 
                        limit=1000
                    )
                    
                    if trades:
                        logger.info(f"   获取到 {len(trades)} 条交易记录")
                        all_trades.extend(trades)
                        # 更新since为最后一条记录的时间
                        since = trades[-1]['timestamp'] + 1
                    else:
                        more_data = False
                        
                except Exception as e:
                    logger.error(f"   获取交易记录时出错: {e}")
                    break
            
            logger.info(f"📊 总计获取到 {len(all_trades)} 条交易记录")
            
            if all_trades:
                logger.info("📈 交易记录时间范围:")
                first_trade_time = pd.to_datetime(all_trades[0]['timestamp'], unit='ms')
                last_trade_time = pd.to_datetime(all_trades[-1]['timestamp'], unit='ms')
                logger.info(f"   第一笔交易: {first_trade_time}")
                logger.info(f"   最后一笔交易: {last_trade_time}")
                
                # 显示前几条和后几条交易
                logger.info("📈 前3条交易记录:")
                for trade in all_trades[:3]:
                    tx_time = pd.to_datetime(trade['timestamp'], unit='ms')
                    side = trade['side']
                    amount = trade['amount']
                    price = trade['price']
                    cost = trade['cost']
                    logger.info(f"   {tx_time}: {side} {amount} BTC @ {price} USDT (总价值: {cost} USDT)")
                
                logger.info("📈 后3条交易记录:")
                for trade in all_trades[-3:]:
                    tx_time = pd.to_datetime(trade['timestamp'], unit='ms')
                    side = trade['side']
                    amount = trade['amount']
                    price = trade['price']
                    cost = trade['cost']
                    logger.info(f"   {tx_time}: {side} {amount} BTC @ {price} USDT (总价值: {cost} USDT)")
        
        # 分析时间范围重叠情况
        logger.info("🔍 时间范围分析:")
        if all_deposits or all_withdrawals:
            usdt_flows = []
            for deposit in all_deposits:
                usdt_flows.append(('deposit', deposit['timestamp'], deposit['amount']))
            for withdrawal in all_withdrawals:
                usdt_flows.append(('withdrawal', withdrawal['timestamp'], withdrawal['amount']))
            
            if usdt_flows:
                usdt_flows.sort(key=lambda x: x[1])
                first_flow = pd.to_datetime(usdt_flows[0][1], unit='ms')
                last_flow = pd.to_datetime(usdt_flows[-1][1], unit='ms')
                logger.info(f"   USDT流水时间范围: {first_flow} 到 {last_flow}")
                
                # 检查是否有在交易时间范围内的USDT流水
                if all_trades:
                    first_trade = pd.to_datetime(all_trades[0]['timestamp'], unit='ms')
                    last_trade = pd.to_datetime(all_trades[-1]['timestamp'], unit='ms')
                    
                    relevant_flows = [flow for flow in usdt_flows 
                                    if first_trade <= pd.to_datetime(flow[1], unit='ms') <= last_trade]
                    logger.info(f"   交易时间范围内的USDT流水: {len(relevant_flows)} 条")
                    
                    if relevant_flows:
                        logger.info("   相关USDT流水详情:")
                        for flow_type, timestamp, amount in relevant_flows:
                            flow_time = pd.to_datetime(timestamp, unit='ms')
                            logger.info(f"     {flow_time}: {flow_type} {amount} USDT")
                    else:
                        logger.warning("⚠️  没有找到在交易时间范围内的USDT流水！")
                        logger.info("   这解释了为什么持仓计算中没有考虑USDT转入转出。")
        
    except Exception as e:
        logger.error(f"❌ 调试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_time_range_and_data()
