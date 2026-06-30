# from . import dm_orchestrators, subiekt_gateway
#
# def final_daily_maintenance():
#     subiekt_conn = subiekt_gateway.get_subiekt_connection()
#
#     try:
#         dm_orchestrators.ingest_recent_zk_rows(subiekt_conn)
#         dm_orchestrators.synchronize_recent_companies()
#         dm_orchestrators.process_warning_candidates()
#         dm_orchestrators.process_stale_candidates()
#     finally:
#         subiekt_conn.close()