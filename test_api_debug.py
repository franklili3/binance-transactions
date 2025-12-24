#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API连接调试脚本
用于诊断币安API认证问题
"""

import os
import ccxt
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_connection():
    """测试API连接"""
    load_dotenv()
    
    # 获取API密钥
    main_api_key = os.getenv('BINANCE_API_KEY')
    main_secret_key = os.getenv('BINANCE_SECRET_KEY')
    copytrade_api_key = os.getenv('BINANCE_COPYTRADE_API_KEY')
    copytrade_secret_key = os.getenv('BINANCE_COPYTRADE_SECRET_KEY')
    
    logger.info("=== API密钥检查 ===")
    logger.info(f"主账户API Key存在: {'是' if main_api_key else '否'}")
    logger.info(f"主账户Secret Key存在: {'是' if main_secret_key else '否'}")
    logger.info(f"带单项目API Key存在: {'是' if copytrade_api_key else '否'}")
    logger.info(f"带单项目Secret Key存在: {'是' if copytrade_secret_key else '否'}")
    
    if main_api_key:
        logger.info(f"主账户API Key长度: {len(main_api_key)}")
        logger.info(f"主账户API Key前8位: {main_api_key[:8]}")
    
    if copytrade_api_key:
        logger.info(f"带单项目API Key长度: {len(copytrade_api_key)}")
        logger.info(f"带单项目API Key前8位: {copytrade_api_key[:8]}")
    
    # 测试主账户API
    logger.info("\n=== 测试主账户API ===")
    if main_api_key and main_secret_key:
        try:
            main_exchange = ccxt.binance({
                'apiKey': main_api_key,
                'secret': main_secret_key,
                'enableRateLimit': True,
            })
            
            # 测试服务器时间（不需要认证）
            logger.info("测试获取服务器时间...")
            server_time = main_exchange.fetch_time()
            logger.info(f"✓ 服务器时间获取成功: {server_time}")
            
            # 测试账户余额（需要认证）
            logger.info("测试获取账户余额...")
            balance = main_exchange.fetch_balance()
            logger.info("✓ 主账户API认证成功")
            logger.info(f"账户信息: {balance.get('info', {}).get('accountType', 'UNKNOWN')}")
            
        except ccxt.AuthenticationError as e:
            logger.error(f"✗ 主账户API认证失败: {e}")
            logger.error("请检查主账户API密钥是否正确")
        except Exception as e:
            logger.error(f"✗ 主账户API测试失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
    else:
        logger.error("主账户API密钥未配置")
    
    # 测试带单项目API
    logger.info("\n=== 测试带单项目API ===")
    if copytrade_api_key and copytrade_secret_key:
        try:
            copytrade_exchange = ccxt.binance({
                'apiKey': copytrade_api_key,
                'secret': copytrade_secret_key,
                'enableRateLimit': True,
            })
            
            # 测试账户余额（需要认证）
            logger.info("测试获取账户余额...")
            balance = copytrade_exchange.fetch_balance()
            logger.info("✓ 带单项目API认证成功")
            logger.info(f"账户信息: {balance.get('info', {}).get('accountType', 'UNKNOWN')}")
            
        except ccxt.AuthenticationError as e:
            logger.error(f"✗ 带单项目API认证失败: {e}")
            logger.error("请检查带单项目API密钥是否正确")
        except Exception as e:
            logger.error(f"✗ 带单项目API测试失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
    else:
        logger.info("带单项目API密钥未配置")

if __name__ == "__main__":
    test_api_connection()
