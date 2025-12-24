#!/usr/bin/env python3
"""
测试USDT转入转出记录获取
"""

import os
import ccxt
import pandas as pd
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_usdt_flows():
    """测试USDT转入转出记录获取"""
    
    # 从环境变量获取API密钥
    main_api_key = os.getenv('BINANCE_API_KEY')
    main_secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if not main_api_key or not main_secret_key:
        logger.error("未找到主账户API密钥")
        return
    
    logger.info(f"主账户API Key: {main_api_key[:10]}...")
    
    # 初始化主账户交易所
    try:
        main_exchange = ccxt.binance({
            'apiKey': main_api_key,
            'secret': main_secret_key,
            'sandbox': False,  # 生产环境
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        logger.info("主账户交易所初始化成功")
    except Exception as e:
        logger.error(f"主账户交易所初始化失败: {e}")
        return
    
    # 测试连接
    try:
        balance = main_exchange.fetch_balance()
        logger.info("主账户API连接成功")
        logger.info(f"账户类型: {main_exchange.options.get('defaultType', 'unknown')}")
    except Exception as e:
        logger.error(f"主账户API连接失败: {e}")
        return
    
    # 获取USDT转入转出记录
    try:
        # 设置时间范围（过去6个月）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        since = int(start_date.timestamp() * 1000)
        
        logger.info(f"获取USDT转入转出记录，时间范围: {start_date} 到 {end_date}")
        
        # 获取充值记录（所有币种）
        logger.info("获取充值记录...")
        deposit_history = main_exchange.fetch_deposits(
            since=since, 
            limit=1000
        )
        logger.info(f"获取到 {len(deposit_history)} 条充值记录")
        
        # 获取提现记录（所有币种）
        logger.info("获取提现记录...")
        withdrawal_history = main_exchange.fetch_withdrawals(
            since=since, 
            limit=1000
        )
        logger.info(f"获取到 {len(withdrawal_history)} 条提现记录")
        
        # 处理充值记录（只保留USDT）
        deposits = []
        for record in deposit_history:
            if record['status'] == 'ok' and record['currency'] == 'USDT':  # 只处理成功的USDT充值
                deposits.append({
                    'timestamp': pd.to_datetime(record['timestamp'], unit='ms'),
                    'type': 'deposit',
                    'amount': record['amount'],
                    'currency': record['currency'],
                    'status': record['status'],
                    'txid': record.get('txid', ''),
                    'info': record.get('info', {})
                })
        
        # 处理提现记录（只保留USDT）
        withdrawals = []
        for record in withdrawal_history:
            if record['status'] == 'ok' and record['currency'] == 'USDT':  # 只处理成功的USDT提现
                withdrawals.append({
                    'timestamp': pd.to_datetime(record['timestamp'], unit='ms'),
                    'type': 'withdrawal',
                    'amount': record['amount'],
                    'currency': record['currency'],
                    'status': record['status'],
                    'txid': record.get('txid', ''),
                    'fee': record.get('fee', 0),
                    'info': record.get('info', {})
                })
        
        # 合并USDT记录
        usdt_flows = deposits + withdrawals
        usdt_flows.sort(key=lambda x: x['timestamp'])
        
        logger.info(f"总共获取到 {len(usdt_flows)} 条USDT转入转出记录")
        
        if usdt_flows:
            logger.info("=== USDT转入转出记录 ===")
            total_deposits = sum(flow['amount'] for flow in usdt_flows if flow['type'] == 'deposit')
            total_withdrawals = sum(flow['amount'] for flow in usdt_flows if flow['type'] == 'withdrawal')
            
            logger.info(f"总充值金额: {total_deposits} USDT")
            logger.info(f"总提现金额: {total_withdrawals} USDT")
            logger.info(f"净流入: {total_deposits - total_withdrawals} USDT")
            
            # 显示前10条记录
            for i, flow in enumerate(usdt_flows[:10]):
                logger.info(f"{i+1}. {flow['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {flow['type']}: {flow['amount']} USDT")
        else:
            logger.warning("没有找到USDT转入转出记录")
            
            # 尝试获取所有币种的记录看看是否有权限问题
            logger.info("尝试获取所有币种的充值记录...")
            try:
                all_deposits = main_exchange.fetch_deposits(since=since, limit=100)
                logger.info(f"所有币种充值记录: {len(all_deposits)} 条")
                if all_deposits:
                    for i, record in enumerate(all_deposits[:5]):
                        logger.info(f"{i+1}. {record['currency']}: {record['amount']} ({record.get('status', 'unknown')})")
            except Exception as e:
                logger.error(f"获取所有币种充值记录失败: {e}")
        
        # 保存到文件
        if usdt_flows:
            df = pd.DataFrame(usdt_flows)
            df.to_csv('usdt_flows_test.csv', index=False)
            logger.info("USDT转入转出记录已保存到 usdt_flows_test.csv")
        
    except Exception as e:
        logger.error(f"获取USDT转入转出记录失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_usdt_flows()
