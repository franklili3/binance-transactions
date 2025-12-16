#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API连接测试脚本
用于诊断币安API连接问题
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

def test_connection():
    """测试API连接"""
    load_dotenv()
    
    # 获取API密钥
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
    
    if api_key:
        logger.info("API Key: {}...".format(api_key[:10]))
    else:
        logger.info("API Key: None")
    
    if secret_key:
        logger.info("Secret Key: {}".format('*' * 10))
    else:
        logger.info("Secret Key: None")
    
    logger.info("Testnet: {}".format(testnet))
    
    if not api_key or not secret_key:
        logger.error("API密钥未设置")
        return False
    
    try:
        # 创建交易所实例
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': testnet,
            'enableRateLimit': True,
            'timeout': 10000,  # 10秒超时
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            },
        })
        
        logger.info("交易所URL: {}".format(exchange.urls['api']['public']))
        logger.info("沙盒模式: {}".format(exchange.sandbox))
        
        # 测试1: 获取服务器时间（不需要认证）
        logger.info("测试1: 获取服务器时间...")
        server_time = exchange.fetch_time()
        logger.info("✓ 服务器时间: {}".format(server_time))
        
        # 测试2: 获取账户信息（需要认证）
        logger.info("测试2: 获取账户信息...")
        balance = exchange.fetch_balance()
        logger.info("✓ 账户信息获取成功")
        
        # 测试3: 获取交易历史
        logger.info("测试3: 获取交易历史...")
        try:
            trades = exchange.fetch_my_trades('BTC/USDT', limit=1)
            logger.info("✓ 交易历史获取成功，共 {} 条记录".format(len(trades)))
        except Exception as e:
            logger.warning("✗ 交易历史获取失败: {}".format(e))
        
        # 测试4: 获取订单历史
        logger.info("测试4: 获取订单历史...")
        try:
            orders = exchange.fetch_orders('BTC/USDT', limit=1)
            logger.info("✓ 订单历史获取成功，共 {} 条记录".format(len(orders)))
        except Exception as e:
            logger.warning("✗ 订单历史获取失败: {}".format(e))
        
        logger.info("所有测试完成")
        return True
        
    except ccxt.AuthenticationError as e:
        logger.error("认证失败: {}".format(e))
        logger.error("请检查API密钥是否正确")
        return False
    except ccxt.PermissionDenied as e:
        logger.error("权限不足: {}".format(e))
        logger.error("请检查API密钥权限设置")
        return False
    except ccxt.NetworkError as e:
        logger.error("网络错误: {}".format(e))
        logger.error("请检查网络连接")
        return False
    except ccxt.ExchangeError as e:
        logger.error("交易所错误: {}".format(e))
        logger.error("可能是API限制或配置问题")
        return False
    except Exception as e:
        logger.error("未知错误: {}".format(e))
        logger.error("错误类型: {}".format(type(e).__name__))
        return False

def suggest_solutions():
    """提供解决方案建议"""
    print("\n=== 解决方案建议 ===")
    print("1. 检查API密钥是否正确复制")
    print("2. 确保API密钥有以下权限：")
    print("   - 读取信息 (Enable Reading)")
    print("   - 现货交易 (Enable Spot & Margin Trading)")
    print("3. 检查IP白名单设置（如果启用了）")
    print("4. 尝试使用测试网:")
    print("   在.env文件中设置: BINANCE_TESTNET=true")
    print("5. 检查网络连接")
    print("6. 确认API密钥没有过期")

if __name__ == "__main__":
    print("币安API连接测试")
    print("=" * 50)
    
    success = test_connection()
    
    if success:
        print("\n✓ API连接测试成功！")
    else:
        print("\n✗ API连接测试失败！")
        suggest_solutions()
