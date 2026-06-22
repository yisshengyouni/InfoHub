import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.feed_parser import fetch_all_feeds

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def job_fetch_all_feeds():
    """定时任务：抓取所有订阅源"""
    try:
        logger.info("[Scheduler] Starting scheduled feed fetch...")
        # fetch_all_feeds 内部会调用 get_db() 且不接受参数
        # 它是一个同步的阻塞函数，所以在 BackgroundScheduler 的线程池中运行是安全的
        result = fetch_all_feeds()
        logger.info(f"[Scheduler] Finished scheduled feed fetch. Result: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] Error during scheduled feed fetch: {e}", exc_info=True)

def start_scheduler():
    """启动定时任务"""
    if not scheduler.running:
        # 每小时抓取一次
        scheduler.add_job(job_fetch_all_feeds, 'interval', hours=1, id="fetch_all_feeds", replace_existing=True)
        scheduler.start()
        logger.info("[Scheduler] Started successfully. Feeds will be fetched every hour.")

def stop_scheduler():
    """停止定时任务"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] Stopped.")
