#!/usr/bin/env python3
"""
简单的API调试脚本
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

def simple_debug():
    """简单调试"""
    
    # 加载环境变量
    load_dotenv()
    
    # 检查环境变量
    logger.info("🔍 检查环境变量...")
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key:
        logger.error("❌ 未找到 BINANCE_API_KEY")
        return
    if not secret_key:
        logger.error("❌ 未找到 BINANCE_SECRET_KEY")
        return
    
    logger.info(f"✅ API密钥存在: {api_key[:10]}...")
    logger.info(f"✅ 密钥存在: {secret_key[:10]}...")
    
    # 初始化交易所
    logger.info("🔍 初始化交易所...")
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret_key,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
        },
    })
    
    try:
        # 测试服务器时间
        logger.info("🔍 获取服务器时间...")
        server_time = exchange.fetch_time()
        logger.info(f"✅ 服务器时间: {pd.to_datetime(server_time, unit='ms')}")
        
        # 测试余额获取（设置超时）
        logger.info("🔍 获取余额（设置超时）...")
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("操作超时")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30秒超时
        
        try:
            balance = exchange.fetch_balance()
            signal.alarm(0)  # 取消超时
            logger.info("✅ 余额获取成功")
            
            # 显示非零余额
            if 'info' in balance and 'balances' in balance['info']:
                for bal in balance['info']['balances']:
                    if float(bal['free']) > 0 or float(bal['locked']) > 0:
                        logger.info(f"   {bal['asset']}: free={bal['free']}, locked={bal['locked']}")
            
        except TimeoutError:
            logger.error("❌ 余额获取超时")
            return
        except Exception as e:
            signal.alarm(0)  # 取消超时
            logger.error(f"❌ 余额获取失败: {e}")
            return
        
        # 测试USDT充值记录获取
        logger.info("🔍 获取USDT充值记录...")
        signal.alarm(30)  # 30秒超时
        
        try:
            deposits = exchange.fetch_deposits(limit=10)
            signal.alarm(0)  # 取消超时
            logger.info(f"✅ 获取到 {len(deposits)} 条充值记录")
            
            # 过滤USDT记录
            usdt_deposits = [d for d in deposits if d['currency'] == 'USDT']
            logger.info(f"   其中USDT充值记录: {len(usdt_deposits)} 条")
            
            for deposit in usdt_deposits[:3]:
                tx_time = pd.to_datetime(deposit['timestamp'], unit='ms')
                amount = deposit['amount']
                status = deposit['status']
                logger.info(f"   {tx_time}: +{amount} USDT (状态: {status})")
                
        except TimeoutError:
            logger.error("❌ USDT充值记录获取超时")
        except Exception as e:
            signal.alarm(0)  # 取消超时
            logger.error(f"❌ USDT充值记录获取失败: {e}")
        
        # 测试USDT提现记录获取
        logger.info("🔍 获取USDT提现记录...")
        signal.alarm(30)  # 30秒超时
        
        try:
            withdrawals = exchange.fetch_withdrawals(limit=10)
            signal.alarm(0)  # 取消超时
            logger.info(f"✅ 获取到 {len(withdrawals)} 条提现记录")
            
            # 过滤USDT记录
            usdt_withdrawals = [w for w in withdrawals if w['currency'] == 'USDT']
            logger.info(f"   其中USDT提现记录: {len(usdt_withdrawals)} 条")
            
            for withdrawal in usdt_withdrawals[:3]:
                tx_time = pd.to_datetime(withdrawal['timestamp'], unit='ms')
                amount = withdrawal['amount']
                status = withdrawal['status']
                logger.info(f"   {tx_time}: -{amount} USDT (状态: {status})")
                
        except TimeoutError:
            logger.error("❌ USDT提现记录获取超时")
        except Exception as e:
            signal.alarm(0)  # 取消超时
            logger.error(f"❌ USDT提现记录获取失败: {e}")
        
        # 测试带单项目API
        logger.info("🔍 检查带单项目API...")
        copytrade_api_key = os.getenv('BINANCE_COPYTRADE_API_KEY')
        copytrade_secret_key = os.getenv('BINANCE_COPYTRADE_SECRET_KEY')
        
        if copytrade_api_key and copytrade_secret_key:
            logger.info("✅ 带单项目API密钥存在")
            
            copytrade_exchange = ccxt.binance({
                'apiKey': copytrade_api_key,
                'secret': copytrade_secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                },
            })
            
            # 测试交易记录获取
            logger.info("🔍 获取BTC/USDT交易记录...")
            signal.alarm(30)  # 30秒超时
            
            try:
                trades = copytrade_exchange.fetch_my_trades(symbol='BTC/USDT', limit=10)
                signal.alarm(0)  # 取消超时
                logger.info(f"✅ 获取到 {len(trades)} 条交易记录")
                
                if trades:
                    first_trade = pd.to_datetime(trades[0]['timestamp'], unit='ms')
                    last_trade = pd.to_datetime(trades[-1]['timestamp'], unit='ms')
                    logger.info(f"   交易时间范围: {first_trade} 到 {last_trade}")
                    
                    for trade in trades[:3]:
                        tx_time = pd.to_datetime(trade['timestamp'], unit='ms')
                        side = trade['side']
                        amount = trade['amount']
                        price = trade['price']
                        logger.info(f"   {tx_time}: {side} {amount} BTC @ {price} USDT")
                        
            except TimeoutError:
                logger.error("❌ 交易记录获取超时")
            except Exception as e:
                signal.alarm(0)  # 取消超时
                logger.error(f"❌ 交易记录获取失败: {e}")
        else:
            logger.warning("⚠️  未找到带单项目API密钥")
        
    except Exception as e:
        logger.error(f"❌ 调试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_debug()
