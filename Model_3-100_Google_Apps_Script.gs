/**
 * MODEL - 3-100 — GOOGLE APPS SCRIPT PAPER-SIGNAL ENGINE
 * BTCUSDT USDT-M perpetual, 1-hour candles; top 100 PF-ranked configurations in one model.
 * PAPER SIGNALS ONLY: this script never submits exchange orders.
 *
 * QUICK START:
 * 1) Paste your Telegram bot token and chat ID in TELEGRAM below.
 * 2) Run startModel3Engine() once and authorize Google permissions.
 * 3) The script creates its own Google Sheet (or uses the active bound Sheet),
 *    sends a Telegram test, starts the 5-minute trigger, and checks the engine.
 * No Script Properties or spreadsheet ID need to be entered manually.
 */
const M3_CONFIGS = [{"model":"Model - 3-100","pf_rank":1,"group_id":5870,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":84,"oos_profit_factor":1.6771906256192224,"oos_net_profit_bps":1478.2646762893162,"oos_max_drawdown_pct":-2.566963815561152,"oos_win_rate_pct":59.523809523809526,"oos_2024_profit_factor":1.368654082568453,"oos_2025_profit_factor":1.6679993690429282,"oos_2026_ytd_profit_factor":2.3441950249488377},{"model":"Model - 3-100","pf_rank":2,"group_id":5288,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"exact","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":61,"oos_profit_factor":1.664590477298754,"oos_net_profit_bps":669.6432429954032,"oos_max_drawdown_pct":-1.8390511864374903,"oos_win_rate_pct":60.65573770491803,"oos_2024_profit_factor":1.5207666508458224,"oos_2025_profit_factor":1.5363112128223009,"oos_2026_ytd_profit_factor":1.9232768887934744},{"model":"Model - 3-100","pf_rank":3,"group_id":5330,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":83,"oos_profit_factor":1.6633430268394058,"oos_net_profit_bps":1440.5546378742956,"oos_max_drawdown_pct":-2.9365391493206494,"oos_win_rate_pct":57.831325301204814,"oos_2024_profit_factor":1.3543674672312864,"oos_2025_profit_factor":2.111396898704842,"oos_2026_ytd_profit_factor":1.865231123914024},{"model":"Model - 3-100","pf_rank":4,"group_id":6410,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":78,"oos_profit_factor":1.657166180870549,"oos_net_profit_bps":1361.7299659032649,"oos_max_drawdown_pct":-4.016110739932888,"oos_win_rate_pct":58.97435897435898,"oos_2024_profit_factor":1.2846117628999345,"oos_2025_profit_factor":1.78326704717276,"oos_2026_ytd_profit_factor":2.243144172594453},{"model":"Model - 3-100","pf_rank":5,"group_id":5398,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":71,"oos_profit_factor":1.6567818086955253,"oos_net_profit_bps":1023.0088005742832,"oos_max_drawdown_pct":-3.545555823916302,"oos_win_rate_pct":49.29577464788733,"oos_2024_profit_factor":0.9443230493265624,"oos_2025_profit_factor":1.765358037046378,"oos_2026_ytd_profit_factor":2.994535181926557},{"model":"Model - 3-100","pf_rank":6,"group_id":5938,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":72,"oos_profit_factor":1.6420621885160962,"oos_net_profit_bps":1021.8472430485808,"oos_max_drawdown_pct":-2.9316413997585777,"oos_win_rate_pct":50.0,"oos_2024_profit_factor":1.1507728163908904,"oos_2025_profit_factor":1.663250833853027,"oos_2026_ytd_profit_factor":2.455295648403024},{"model":"Model - 3-100","pf_rank":7,"group_id":5334,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":70,"oos_profit_factor":1.6397125470194116,"oos_net_profit_bps":939.1625081093669,"oos_max_drawdown_pct":-4.15967588947982,"oos_win_rate_pct":60.0,"oos_2024_profit_factor":0.9167398863159252,"oos_2025_profit_factor":1.397285595015325,"oos_2026_ytd_profit_factor":4.36193733968534},{"model":"Model - 3-100","pf_rank":8,"group_id":5398,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":4.0,"pending_bars":3,"oos_trades":71,"oos_profit_factor":1.6345017798775905,"oos_net_profit_bps":1143.5625147899118,"oos_max_drawdown_pct":-3.225470383364326,"oos_win_rate_pct":40.845070422535215,"oos_2024_profit_factor":1.0241073634123568,"oos_2025_profit_factor":2.4422557929990645,"oos_2026_ytd_profit_factor":1.9131182999908247},{"model":"Model - 3-100","pf_rank":9,"group_id":5938,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":4.0,"pending_bars":3,"oos_trades":72,"oos_profit_factor":1.600710036644948,"oos_net_profit_bps":1108.9139932838857,"oos_max_drawdown_pct":-2.7517952162972925,"oos_win_rate_pct":41.66666666666667,"oos_2024_profit_factor":1.0469966833008997,"oos_2025_profit_factor":2.3103411000582943,"oos_2026_ytd_profit_factor":1.7525928384894809},{"model":"Model - 3-100","pf_rank":10,"group_id":5336,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.82,"rr":3.0,"pending_bars":3,"oos_trades":64,"oos_profit_factor":1.5914183505006074,"oos_net_profit_bps":949.584203694101,"oos_max_drawdown_pct":-3.737401980320132,"oos_win_rate_pct":48.4375,"oos_2024_profit_factor":0.8328174197310196,"oos_2025_profit_factor":1.5999880770739558,"oos_2026_ytd_profit_factor":3.207042647107351},{"model":"Model - 3-100","pf_rank":11,"group_id":5198,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"exact","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":70,"oos_profit_factor":1.5856696034270037,"oos_net_profit_bps":677.7040774765857,"oos_max_drawdown_pct":-1.983340878903994,"oos_win_rate_pct":60.0,"oos_2024_profit_factor":1.4854531972666265,"oos_2025_profit_factor":1.5409638622312576,"oos_2026_ytd_profit_factor":1.7412100722747794},{"model":"Model - 3-100","pf_rank":12,"group_id":5874,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":71,"oos_profit_factor":1.5831540660528372,"oos_net_profit_bps":882.9875320370634,"oos_max_drawdown_pct":-4.200616109529854,"oos_win_rate_pct":60.56338028169014,"oos_2024_profit_factor":0.9017753922938506,"oos_2025_profit_factor":1.1362363532906885,"oos_2026_ytd_profit_factor":5.140614415833672},{"model":"Model - 3-100","pf_rank":13,"group_id":6328,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":70,"oos_profit_factor":1.5757596302697363,"oos_net_profit_bps":856.4847239725534,"oos_max_drawdown_pct":-4.287186648213737,"oos_win_rate_pct":48.57142857142857,"oos_2024_profit_factor":1.597527621110186,"oos_2025_profit_factor":0.6614668489425353,"oos_2026_ytd_profit_factor":3.659552867838964},{"model":"Model - 3-100","pf_rank":14,"group_id":6478,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":68,"oos_profit_factor":1.5695837508247148,"oos_net_profit_bps":890.974463088808,"oos_max_drawdown_pct":-2.77112246544573,"oos_win_rate_pct":48.52941176470589,"oos_2024_profit_factor":1.101623759536581,"oos_2025_profit_factor":1.6097721928481072,"oos_2026_ytd_profit_factor":2.2627884966138594},{"model":"Model - 3-100","pf_rank":15,"group_id":5398,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":71,"oos_profit_factor":1.565991955226125,"oos_net_profit_bps":705.452379958128,"oos_max_drawdown_pct":-2.3370710716282272,"oos_win_rate_pct":59.15492957746479,"oos_2024_profit_factor":1.2025507837725664,"oos_2025_profit_factor":1.287335025999658,"oos_2026_ytd_profit_factor":2.663154205418018},{"model":"Model - 3-100","pf_rank":16,"group_id":5938,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":72,"oos_profit_factor":1.5387567137640097,"oos_net_profit_bps":689.7701743464694,"oos_max_drawdown_pct":-2.7517952162972925,"oos_win_rate_pct":59.72222222222222,"oos_2024_profit_factor":1.467506168412132,"oos_2025_profit_factor":1.1792082894794182,"oos_2026_ytd_profit_factor":2.166005694281845},{"model":"Model - 3-100","pf_rank":17,"group_id":6320,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":101,"oos_profit_factor":1.5358135365227377,"oos_net_profit_bps":1475.0172816397985,"oos_max_drawdown_pct":-3.5649798192098348,"oos_win_rate_pct":55.44554455445545,"oos_2024_profit_factor":1.3432020593850538,"oos_2025_profit_factor":1.7758135714306476,"oos_2026_ytd_profit_factor":1.6145181571925835},{"model":"Model - 3-100","pf_rank":18,"group_id":6230,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":121,"oos_profit_factor":1.5332529621758924,"oos_net_profit_bps":1693.1521617735664,"oos_max_drawdown_pct":-3.1582939322207797,"oos_win_rate_pct":54.54545454545454,"oos_2024_profit_factor":1.502026349925325,"oos_2025_profit_factor":1.7947932515311733,"oos_2026_ytd_profit_factor":1.3196939817449873},{"model":"Model - 3-100","pf_rank":19,"group_id":5328,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.85,"rr":3.0,"pending_bars":6,"oos_trades":74,"oos_profit_factor":1.5264361821247403,"oos_net_profit_bps":815.2767764942384,"oos_max_drawdown_pct":-2.9319020586691336,"oos_win_rate_pct":48.64864864864865,"oos_2024_profit_factor":1.1916660060487985,"oos_2025_profit_factor":0.912892403986633,"oos_2026_ytd_profit_factor":3.511615118506508},{"model":"Model - 3-100","pf_rank":20,"group_id":5218,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":106,"oos_profit_factor":1.522785620613823,"oos_net_profit_bps":1207.6961995069105,"oos_max_drawdown_pct":-3.1369171901832527,"oos_win_rate_pct":46.22641509433962,"oos_2024_profit_factor":1.1982217846371783,"oos_2025_profit_factor":1.407689024696705,"oos_2026_ytd_profit_factor":2.183985523634232},{"model":"Model - 3-100","pf_rank":21,"group_id":6140,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.2,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":175,"oos_profit_factor":1.514813030610611,"oos_net_profit_bps":2267.103151391426,"oos_max_drawdown_pct":-3.5896156049583183,"oos_win_rate_pct":53.142857142857146,"oos_2024_profit_factor":1.624699900358071,"oos_2025_profit_factor":1.6692817094406662,"oos_2026_ytd_profit_factor":1.2377667932558245},{"model":"Model - 3-100","pf_rank":22,"group_id":6478,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":4.0,"pending_bars":3,"oos_trades":68,"oos_profit_factor":1.5125095956881172,"oos_net_profit_bps":932.1281787984644,"oos_max_drawdown_pct":-2.785724006473689,"oos_win_rate_pct":39.70588235294117,"oos_2024_profit_factor":0.9613827670072328,"oos_2025_profit_factor":2.230972641321278,"oos_2026_ytd_profit_factor":1.6158232894956828},{"model":"Model - 3-100","pf_rank":23,"group_id":5876,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.82,"rr":3.0,"pending_bars":3,"oos_trades":64,"oos_profit_factor":1.5038749156578353,"oos_net_profit_bps":829.8896005449802,"oos_max_drawdown_pct":-4.119619925992469,"oos_win_rate_pct":48.4375,"oos_2024_profit_factor":0.76106638528951,"oos_2025_profit_factor":1.372374842021488,"oos_2026_ytd_profit_factor":3.342856175839058},{"model":"Model - 3-100","pf_rank":24,"group_id":6324,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":86,"oos_profit_factor":1.503386378820511,"oos_net_profit_bps":951.0276180137062,"oos_max_drawdown_pct":-3.798833883070485,"oos_win_rate_pct":58.13953488372093,"oos_2024_profit_factor":1.2089537512322055,"oos_2025_profit_factor":0.8537594269843687,"oos_2026_ytd_profit_factor":3.9734804179009737},{"model":"Model - 3-100","pf_rank":25,"group_id":6414,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":66,"oos_profit_factor":1.502062328831746,"oos_net_profit_bps":738.4009944625892,"oos_max_drawdown_pct":-4.909682415066774,"oos_win_rate_pct":59.09090909090909,"oos_2024_profit_factor":0.7842161469315047,"oos_2025_profit_factor":1.1006762203167009,"oos_2026_ytd_profit_factor":4.908503013769945},{"model":"Model - 3-100","pf_rank":26,"group_id":6478,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":68,"oos_profit_factor":1.4982478151486556,"oos_net_profit_bps":624.3279873723667,"oos_max_drawdown_pct":-2.7517952162972814,"oos_win_rate_pct":58.82352941176471,"oos_2024_profit_factor":1.4843601145090526,"oos_2025_profit_factor":1.1494679605446705,"oos_2026_ytd_profit_factor":2.0050992167177526},{"model":"Model - 3-100","pf_rank":27,"group_id":5780,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":100,"oos_profit_factor":1.4940369886637836,"oos_net_profit_bps":1342.0937125789342,"oos_max_drawdown_pct":-3.564979819209813,"oos_win_rate_pct":55.00000000000001,"oos_2024_profit_factor":1.1566891907605428,"oos_2025_profit_factor":1.8779078853572408,"oos_2026_ytd_profit_factor":1.6842877837967842},{"model":"Model - 3-100","pf_rank":28,"group_id":5930,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":99,"oos_profit_factor":1.4934038576970077,"oos_net_profit_bps":1436.4043936760047,"oos_max_drawdown_pct":-5.430815325888827,"oos_win_rate_pct":55.55555555555556,"oos_2024_profit_factor":1.2515150653414424,"oos_2025_profit_factor":2.305746995029022,"oos_2026_ytd_profit_factor":1.2739291146644889},{"model":"Model - 3-100","pf_rank":29,"group_id":5600,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.2,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":179,"oos_profit_factor":1.4839694893047763,"oos_net_profit_bps":2191.577068260908,"oos_max_drawdown_pct":-3.5896156049583072,"oos_win_rate_pct":53.072625698324025,"oos_2024_profit_factor":1.524534773972,"oos_2025_profit_factor":1.715105567168094,"oos_2026_ytd_profit_factor":1.205858433749359},{"model":"Model - 3-100","pf_rank":30,"group_id":6238,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":85,"oos_profit_factor":1.4838304294011644,"oos_net_profit_bps":860.8504467774569,"oos_max_drawdown_pct":-4.910832238862072,"oos_win_rate_pct":47.05882352941176,"oos_2024_profit_factor":1.5075822115905195,"oos_2025_profit_factor":0.7378222343503837,"oos_2026_ytd_profit_factor":2.899717885631833},{"model":"Model - 3-100","pf_rank":31,"group_id":6234,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":104,"oos_profit_factor":1.4826150550150043,"oos_net_profit_bps":1057.3703612573684,"oos_max_drawdown_pct":-2.8857062810073053,"oos_win_rate_pct":57.692307692307686,"oos_2024_profit_factor":1.3225086912637736,"oos_2025_profit_factor":0.8663170958789991,"oos_2026_ytd_profit_factor":3.108691982314033},{"model":"Model - 3-100","pf_rank":32,"group_id":5150,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":127,"oos_profit_factor":1.48242867565059,"oos_net_profit_bps":1620.6315361150416,"oos_max_drawdown_pct":-3.6101063619885743,"oos_win_rate_pct":52.75590551181102,"oos_2024_profit_factor":1.4272458097379326,"oos_2025_profit_factor":1.5373785237350512,"oos_2026_ytd_profit_factor":1.5096307119365602},{"model":"Model - 3-100","pf_rank":33,"group_id":5198,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"exact","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":70,"oos_profit_factor":1.48169402931035,"oos_net_profit_bps":742.1466037292779,"oos_max_drawdown_pct":-3.2273431320497314,"oos_win_rate_pct":47.14285714285714,"oos_2024_profit_factor":0.9559283066764468,"oos_2025_profit_factor":2.100909849531105,"oos_2026_ytd_profit_factor":1.791271060808458},{"model":"Model - 3-100","pf_rank":34,"group_id":5138,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":63,"oos_profit_factor":1.4773063691400057,"oos_net_profit_bps":621.9251575804872,"oos_max_drawdown_pct":-3.2959014480568816,"oos_win_rate_pct":46.03174603174603,"oos_2024_profit_factor":1.4232946142087115,"oos_2025_profit_factor":0.7535033204554297,"oos_2026_ytd_profit_factor":2.7241724706265527},{"model":"Model - 3-100","pf_rank":35,"group_id":5758,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":106,"oos_profit_factor":1.4767316041493146,"oos_net_profit_bps":1118.1695960951115,"oos_max_drawdown_pct":-3.612671519014221,"oos_win_rate_pct":45.28301886792453,"oos_2024_profit_factor":1.1067832844608496,"oos_2025_profit_factor":1.4267026529410358,"oos_2026_ytd_profit_factor":2.0833306646556915},{"model":"Model - 3-100","pf_rank":36,"group_id":5390,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":96,"oos_profit_factor":1.4758452345428814,"oos_net_profit_bps":1350.494796521176,"oos_max_drawdown_pct":-5.249853554039996,"oos_win_rate_pct":54.16666666666666,"oos_2024_profit_factor":1.2256563250103354,"oos_2025_profit_factor":2.6280848081451587,"oos_2026_ytd_profit_factor":1.172458321926667},{"model":"Model - 3-100","pf_rank":37,"group_id":5660,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.2,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":205,"oos_profit_factor":1.4751744043159651,"oos_net_profit_bps":2608.9300189596443,"oos_max_drawdown_pct":-5.21462576958206,"oos_win_rate_pct":51.707317073170735,"oos_2024_profit_factor":1.307574838199088,"oos_2025_profit_factor":2.316140857766197,"oos_2026_ytd_profit_factor":1.0989929076655156},{"model":"Model - 3-100","pf_rank":38,"group_id":5336,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.82,"rr":2.0,"pending_bars":3,"oos_trades":64,"oos_profit_factor":1.4751731263629684,"oos_net_profit_bps":626.4322005605254,"oos_max_drawdown_pct":-3.378388524786957,"oos_win_rate_pct":57.8125,"oos_2024_profit_factor":0.8235590836904388,"oos_2025_profit_factor":1.2018987775982417,"oos_2026_ytd_profit_factor":3.8706687219753126},{"model":"Model - 3-100","pf_rank":39,"group_id":6388,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":88,"oos_profit_factor":1.4700281842149452,"oos_net_profit_bps":958.5054366417658,"oos_max_drawdown_pct":-3.4678864225292205,"oos_win_rate_pct":45.45454545454545,"oos_2024_profit_factor":1.1752162674578963,"oos_2025_profit_factor":1.326304977332523,"oos_2026_ytd_profit_factor":2.1347270694812144},{"model":"Model - 3-100","pf_rank":40,"group_id":6290,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":145,"oos_profit_factor":1.46536618974705,"oos_net_profit_bps":1896.3707309210567,"oos_max_drawdown_pct":-4.926319282193248,"oos_win_rate_pct":52.41379310344828,"oos_2024_profit_factor":1.1992462972386269,"oos_2025_profit_factor":2.5989834040002093,"oos_2026_ytd_profit_factor":1.1594727854144558},{"model":"Model - 3-100","pf_rank":41,"group_id":6200,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.2,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":202,"oos_profit_factor":1.4635145738715205,"oos_net_profit_bps":2531.163995498771,"oos_max_drawdown_pct":-5.214625769582026,"oos_win_rate_pct":50.99009900990099,"oos_2024_profit_factor":1.2386301055567208,"oos_2025_profit_factor":2.2978456235675506,"oos_2026_ytd_profit_factor":1.1272474750890984},{"model":"Model - 3-100","pf_rank":42,"group_id":5308,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":91,"oos_profit_factor":1.4615444454324846,"oos_net_profit_bps":937.173204574372,"oos_max_drawdown_pct":-3.43059854409552,"oos_win_rate_pct":46.15384615384615,"oos_2024_profit_factor":0.9702756781811904,"oos_2025_profit_factor":1.3571309787379005,"oos_2026_ytd_profit_factor":2.459421108735929},{"model":"Model - 3-100","pf_rank":43,"group_id":6214,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":70,"oos_profit_factor":1.459051565596074,"oos_net_profit_bps":687.8054096704648,"oos_max_drawdown_pct":-3.6541547733438096,"oos_win_rate_pct":57.14285714285714,"oos_2024_profit_factor":1.1113187731284404,"oos_2025_profit_factor":1.0591598509688491,"oos_2026_ytd_profit_factor":2.92573967580042},{"model":"Model - 3-100","pf_rank":44,"group_id":5398,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":5.0,"pending_bars":3,"oos_trades":70,"oos_profit_factor":1.454493137498993,"oos_net_profit_bps":917.7525613437274,"oos_max_drawdown_pct":-4.067906800897858,"oos_win_rate_pct":32.857142857142854,"oos_2024_profit_factor":0.8600276525309245,"oos_2025_profit_factor":1.6681596952944229,"oos_2026_ytd_profit_factor":2.2006241572745533},{"model":"Model - 3-100","pf_rank":45,"group_id":6470,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":94,"oos_profit_factor":1.4532129707817585,"oos_net_profit_bps":1284.9873233424664,"oos_max_drawdown_pct":-4.948416032982306,"oos_win_rate_pct":54.25531914893617,"oos_2024_profit_factor":1.187598151688389,"oos_2025_profit_factor":2.492842416560701,"oos_2026_ytd_profit_factor":1.1684366659213288},{"model":"Model - 3-100","pf_rank":46,"group_id":6298,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":104,"oos_profit_factor":1.4530183967170305,"oos_net_profit_bps":1065.6587384165778,"oos_max_drawdown_pct":-3.832562483319135,"oos_win_rate_pct":45.19230769230769,"oos_2024_profit_factor":1.0964728094631064,"oos_2025_profit_factor":1.3956389556845643,"oos_2026_ytd_profit_factor":2.0991812846283406},{"model":"Model - 3-100","pf_rank":47,"group_id":5288,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"exact","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":61,"oos_profit_factor":1.4511216322458764,"oos_net_profit_bps":627.5824065175494,"oos_max_drawdown_pct":-3.642774003965577,"oos_win_rate_pct":45.90163934426229,"oos_2024_profit_factor":0.8863211989839944,"oos_2025_profit_factor":1.977877612811127,"oos_2026_ytd_profit_factor":1.9315938977167808},{"model":"Model - 3-100","pf_rank":48,"group_id":5240,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":111,"oos_profit_factor":1.4480204605010825,"oos_net_profit_bps":1344.5565315373883,"oos_max_drawdown_pct":-3.933947983605268,"oos_win_rate_pct":53.15315315315316,"oos_2024_profit_factor":1.2359605798110609,"oos_2025_profit_factor":1.7252167139781,"oos_2026_ytd_profit_factor":1.5191340304853884},{"model":"Model - 3-100","pf_rank":49,"group_id":5690,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":127,"oos_profit_factor":1.447297355104864,"oos_net_profit_bps":1514.0681070398932,"oos_max_drawdown_pct":-3.5896156049583183,"oos_win_rate_pct":52.75590551181102,"oos_2024_profit_factor":1.2978975946172515,"oos_2025_profit_factor":1.7492191724551671,"oos_2026_ytd_profit_factor":1.3846139779274311},{"model":"Model - 3-100","pf_rank":50,"group_id":5324,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.8,"rr":2.0,"pending_bars":6,"oos_trades":79,"oos_profit_factor":1.4456129635668098,"oos_net_profit_bps":779.4074813260582,"oos_max_drawdown_pct":-3.93155042312312,"oos_win_rate_pct":56.9620253164557,"oos_2024_profit_factor":0.8758952098855431,"oos_2025_profit_factor":1.4047216615658331,"oos_2026_ytd_profit_factor":3.106244244180512},{"model":"Model - 3-100","pf_rank":51,"group_id":6228,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":68,"oos_profit_factor":1.4362661503302094,"oos_net_profit_bps":635.1920132098738,"oos_max_drawdown_pct":-3.9306627000665895,"oos_win_rate_pct":47.05882352941176,"oos_2024_profit_factor":1.1501998425380684,"oos_2025_profit_factor":0.7941071861835547,"oos_2026_ytd_profit_factor":3.425774572252735},{"model":"Model - 3-100","pf_rank":52,"group_id":6380,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":122,"oos_profit_factor":1.432038083948244,"oos_net_profit_bps":1547.6638008606224,"oos_max_drawdown_pct":-6.610131930868479,"oos_win_rate_pct":52.459016393442624,"oos_2024_profit_factor":1.1651584769492105,"oos_2025_profit_factor":2.64608691250241,"oos_2026_ytd_profit_factor":1.0737594676690645},{"model":"Model - 3-100","pf_rank":53,"group_id":5938,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":5.0,"pending_bars":3,"oos_trades":71,"oos_profit_factor":1.4307771508625011,"oos_net_profit_bps":888.6904855104018,"oos_max_drawdown_pct":-4.815283910016688,"oos_win_rate_pct":33.80281690140845,"oos_2024_profit_factor":0.8730762755177904,"oos_2025_profit_factor":1.7071737159602751,"oos_2026_ytd_profit_factor":1.9952216420888889},{"model":"Model - 3-100","pf_rank":54,"group_id":6440,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":15,"adx_max":25,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":68,"oos_profit_factor":1.429420882477599,"oos_net_profit_bps":846.4531160251322,"oos_max_drawdown_pct":-3.235638828017051,"oos_win_rate_pct":54.41176470588235,"oos_2024_profit_factor":1.3780831912364,"oos_2025_profit_factor":1.0131977153319005,"oos_2026_ytd_profit_factor":2.3075578205330727},{"model":"Model - 3-100","pf_rank":55,"group_id":6416,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.82,"rr":3.0,"pending_bars":3,"oos_trades":60,"oos_profit_factor":1.4291360599318428,"oos_net_profit_bps":689.4187180789545,"oos_max_drawdown_pct":-4.536579001051333,"oos_win_rate_pct":46.66666666666666,"oos_2024_profit_factor":0.6746645235152569,"oos_2025_profit_factor":1.316498019078799,"oos_2026_ytd_profit_factor":3.1684688957844096},{"model":"Model - 3-100","pf_rank":56,"group_id":5210,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":144,"oos_profit_factor":1.4195570400345363,"oos_net_profit_bps":1718.4348039015763,"oos_max_drawdown_pct":-6.653833501818751,"oos_win_rate_pct":50.69444444444444,"oos_2024_profit_factor":1.2683487418229469,"oos_2025_profit_factor":2.159120427959688,"oos_2026_ytd_profit_factor":1.086162136119346},{"model":"Model - 3-100","pf_rank":57,"group_id":5158,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":92,"oos_profit_factor":1.418806946719636,"oos_net_profit_bps":807.6779607564091,"oos_max_drawdown_pct":-4.682618958191787,"oos_win_rate_pct":45.65217391304348,"oos_2024_profit_factor":1.4140616011632987,"oos_2025_profit_factor":0.6787796340763598,"oos_2026_ytd_profit_factor":2.9023606627863625},{"model":"Model - 3-100","pf_rank":58,"group_id":5320,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":62,"oos_profit_factor":1.41518883234369,"oos_net_profit_bps":743.6240091950283,"oos_max_drawdown_pct":-2.9365391493206605,"oos_win_rate_pct":54.83870967741935,"oos_2024_profit_factor":0.931923948790966,"oos_2025_profit_factor":2.740729583326421,"oos_2026_ytd_profit_factor":1.4834224016466098},{"model":"Model - 3-100","pf_rank":59,"group_id":5326,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.82,"rr":3.0,"pending_bars":6,"oos_trades":79,"oos_profit_factor":1.4136981634220829,"oos_net_profit_bps":826.9109008143276,"oos_max_drawdown_pct":-3.656680347449859,"oos_win_rate_pct":45.56962025316456,"oos_2024_profit_factor":0.8642268822669418,"oos_2025_profit_factor":1.6449579290747791,"oos_2026_ytd_profit_factor":2.247855228996788},{"model":"Model - 3-100","pf_rank":60,"group_id":5604,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.2,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":153,"oos_profit_factor":1.4130584619896442,"oos_net_profit_bps":1289.8294364905082,"oos_max_drawdown_pct":-3.644443736407077,"oos_win_rate_pct":55.55555555555556,"oos_2024_profit_factor":1.4827957135960463,"oos_2025_profit_factor":0.899107141499974,"oos_2026_ytd_profit_factor":2.065794445076373},{"model":"Model - 3-100","pf_rank":61,"group_id":5840,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":118,"oos_profit_factor":1.4127097730366684,"oos_net_profit_bps":1427.1151426408692,"oos_max_drawdown_pct":-6.610131930868457,"oos_win_rate_pct":52.54237288135594,"oos_2024_profit_factor":1.0631211430793783,"oos_2025_profit_factor":2.7942462939682424,"oos_2026_ytd_profit_factor":1.0729789849945253},{"model":"Model - 3-100","pf_rank":62,"group_id":6144,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.2,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":146,"oos_profit_factor":1.4092640685868705,"oos_net_profit_bps":1228.4799113181443,"oos_max_drawdown_pct":-3.5018419771682074,"oos_win_rate_pct":55.47945205479452,"oos_2024_profit_factor":1.3753262103988186,"oos_2025_profit_factor":0.9462399200832212,"oos_2026_ytd_profit_factor":2.12642887543595},{"model":"Model - 3-100","pf_rank":63,"group_id":5218,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":106,"oos_profit_factor":1.4082192146548689,"oos_net_profit_bps":763.2905657427319,"oos_max_drawdown_pct":-2.697768237550391,"oos_win_rate_pct":56.60377358490566,"oos_2024_profit_factor":1.3659508355656698,"oos_2025_profit_factor":1.097279637890713,"oos_2026_ytd_profit_factor":1.899336465673083},{"model":"Model - 3-100","pf_rank":64,"group_id":6110,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.0,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":274,"oos_profit_factor":1.406207651923271,"oos_net_profit_bps":2897.499812057305,"oos_max_drawdown_pct":-5.761007329858236,"oos_win_rate_pct":49.63503649635037,"oos_2024_profit_factor":1.4776101899708345,"oos_2025_profit_factor":1.8363936190846732,"oos_2026_ytd_profit_factor":0.909034465529408},{"model":"Model - 3-100","pf_rank":65,"group_id":5396,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.82,"rr":3.0,"pending_bars":3,"oos_trades":77,"oos_profit_factor":1.4050082023787265,"oos_net_profit_bps":878.1478820427776,"oos_max_drawdown_pct":-4.606209121979099,"oos_win_rate_pct":44.15584415584416,"oos_2024_profit_factor":0.6703043601749704,"oos_2025_profit_factor":2.444102881075493,"oos_2026_ytd_profit_factor":1.9312667047012968},{"model":"Model - 3-100","pf_rank":66,"group_id":5314,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.8,"rr":2.0,"pending_bars":6,"oos_trades":60,"oos_profit_factor":1.404838880510854,"oos_net_profit_bps":558.3518417377805,"oos_max_drawdown_pct":-2.998708823771301,"oos_win_rate_pct":55.00000000000001,"oos_2024_profit_factor":0.8635852768496145,"oos_2025_profit_factor":1.2423120216604229,"oos_2026_ytd_profit_factor":3.214740199166824},{"model":"Model - 3-100","pf_rank":67,"group_id":6326,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.82,"rr":3.0,"pending_bars":3,"oos_trades":77,"oos_profit_factor":1.4046323440525137,"oos_net_profit_bps":827.4963389476347,"oos_max_drawdown_pct":-3.799710213375396,"oos_win_rate_pct":45.45454545454545,"oos_2024_profit_factor":1.1056549769484278,"oos_2025_profit_factor":1.0510857457213512,"oos_2026_ytd_profit_factor":2.502902867782723},{"model":"Model - 3-100","pf_rank":68,"group_id":5338,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":6,"oos_trades":93,"oos_profit_factor":1.403260957230028,"oos_net_profit_bps":808.6128535340949,"oos_max_drawdown_pct":-4.792680714681252,"oos_win_rate_pct":46.236559139784944,"oos_2024_profit_factor":0.946147412384502,"oos_2025_profit_factor":0.9135783417078456,"oos_2026_ytd_profit_factor":3.1804114574850804},{"model":"Model - 3-100","pf_rank":69,"group_id":5138,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":63,"oos_profit_factor":1.4021953861254477,"oos_net_profit_bps":420.5552036053992,"oos_max_drawdown_pct":-3.680738906060888,"oos_win_rate_pct":55.55555555555556,"oos_2024_profit_factor":1.888582271298593,"oos_2025_profit_factor":0.5562359760129993,"oos_2026_ytd_profit_factor":2.444687289504388},{"model":"Model - 3-100","pf_rank":70,"group_id":5570,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.0,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":269,"oos_profit_factor":1.4009842256256997,"oos_net_profit_bps":2805.1353229913834,"oos_max_drawdown_pct":-5.445472556912046,"oos_win_rate_pct":49.44237918215613,"oos_2024_profit_factor":1.4850895960204633,"oos_2025_profit_factor":1.771450375746768,"oos_2026_ytd_profit_factor":0.9327846662156304},{"model":"Model - 3-100","pf_rank":71,"group_id":6278,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"exact","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":64,"oos_profit_factor":1.395464820090323,"oos_net_profit_bps":581.8324351203577,"oos_max_drawdown_pct":-3.72892595501697,"oos_win_rate_pct":45.3125,"oos_2024_profit_factor":0.879484376222395,"oos_2025_profit_factor":2.2731896173433377,"oos_2026_ytd_profit_factor":1.673697460221674},{"model":"Model - 3-100","pf_rank":72,"group_id":5308,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":2.0,"pending_bars":3,"oos_trades":91,"oos_profit_factor":1.3949798525817476,"oos_net_profit_bps":641.3384891382334,"oos_max_drawdown_pct":-2.73989661731201,"oos_win_rate_pct":57.14285714285714,"oos_2024_profit_factor":1.2503282326923586,"oos_2025_profit_factor":0.9929408834307766,"oos_2026_ytd_profit_factor":2.2661077184230365},{"model":"Model - 3-100","pf_rank":73,"group_id":5238,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":66,"oos_profit_factor":1.3941855835819603,"oos_net_profit_bps":563.8864328878641,"oos_max_drawdown_pct":-4.296786993728363,"oos_win_rate_pct":45.45454545454545,"oos_2024_profit_factor":1.0024022000964468,"oos_2025_profit_factor":0.7447218852255778,"oos_2026_ytd_profit_factor":3.262850416533775},{"model":"Model - 3-100","pf_rank":74,"group_id":6208,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.2,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":144,"oos_profit_factor":1.3924321361197118,"oos_net_profit_bps":1231.4812274880055,"oos_max_drawdown_pct":-4.027761752806159,"oos_win_rate_pct":43.75,"oos_2024_profit_factor":1.158564200739363,"oos_2025_profit_factor":1.4155938583619962,"oos_2026_ytd_profit_factor":1.667888166859363},{"model":"Model - 3-100","pf_rank":75,"group_id":6260,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":15,"adx_max":25,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":108,"oos_profit_factor":1.391447321099095,"oos_net_profit_bps":1179.0857199653117,"oos_max_drawdown_pct":-3.61425829682005,"oos_win_rate_pct":51.85185185185185,"oos_2024_profit_factor":1.6504125656953303,"oos_2025_profit_factor":0.8857212601848392,"oos_2026_ytd_profit_factor":2.0731630906219607},{"model":"Model - 3-100","pf_rank":76,"group_id":5876,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.82,"rr":2.0,"pending_bars":3,"oos_trades":64,"oos_profit_factor":1.3914198377352531,"oos_net_profit_bps":532.2269957569735,"oos_max_drawdown_pct":-3.381595673457272,"oos_win_rate_pct":57.8125,"oos_2024_profit_factor":0.802920488979125,"oos_2025_profit_factor":0.9886487967595344,"oos_2026_ytd_profit_factor":4.34874160161335},{"model":"Model - 3-100","pf_rank":77,"group_id":6294,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":124,"oos_profit_factor":1.3843820883931282,"oos_net_profit_bps":1114.7730189817712,"oos_max_drawdown_pct":-5.139236938071812,"oos_win_rate_pct":54.83870967741935,"oos_2024_profit_factor":0.921204286107724,"oos_2025_profit_factor":1.3929475948716408,"oos_2026_ytd_profit_factor":2.3023591792122864},{"model":"Model - 3-100","pf_rank":78,"group_id":6236,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.82,"rr":3.0,"pending_bars":3,"oos_trades":95,"oos_profit_factor":1.3810365999603464,"oos_net_profit_bps":921.809399883794,"oos_max_drawdown_pct":-3.034146303462648,"oos_win_rate_pct":44.21052631578947,"oos_2024_profit_factor":1.335791556871278,"oos_2025_profit_factor":1.0987234091923048,"oos_2026_ytd_profit_factor":1.8047918858490453},{"model":"Model - 3-100","pf_rank":79,"group_id":6224,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":83,"oos_profit_factor":1.380743661740056,"oos_net_profit_bps":707.5294332994364,"oos_max_drawdown_pct":-3.697654687687713,"oos_win_rate_pct":56.62650602409639,"oos_2024_profit_factor":1.0897205154177942,"oos_2025_profit_factor":0.9043878805381595,"oos_2026_ytd_profit_factor":3.083916698897421},{"model":"Model - 3-100","pf_rank":80,"group_id":6204,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.2,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":168,"oos_profit_factor":1.3791891096481117,"oos_net_profit_bps":1429.9660292550543,"oos_max_drawdown_pct":-5.801873334614783,"oos_win_rate_pct":53.57142857142857,"oos_2024_profit_factor":0.962241546317042,"oos_2025_profit_factor":1.581338409849201,"oos_2026_ytd_profit_factor":1.8356644713631225},{"model":"Model - 3-100","pf_rank":81,"group_id":5694,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":110,"oos_profit_factor":1.379011383737275,"oos_net_profit_bps":900.1891439696628,"oos_max_drawdown_pct":-3.585262806013889,"oos_win_rate_pct":55.45454545454545,"oos_2024_profit_factor":1.029529861932034,"oos_2025_profit_factor":0.9175347728932036,"oos_2026_ytd_profit_factor":3.0782900919990817},{"model":"Model - 3-100","pf_rank":82,"group_id":5360,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":15,"adx_max":25,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":72,"oos_profit_factor":1.377452643183092,"oos_net_profit_bps":794.7280842791326,"oos_max_drawdown_pct":-3.614258296820039,"oos_win_rate_pct":52.77777777777778,"oos_2024_profit_factor":1.245491535857719,"oos_2025_profit_factor":0.9981856618430942,"oos_2026_ytd_profit_factor":2.4069025949753837},{"model":"Model - 3-100","pf_rank":83,"group_id":6314,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":69,"oos_profit_factor":1.3773779512649225,"oos_net_profit_bps":609.2111614066395,"oos_max_drawdown_pct":-3.6500376922366073,"oos_win_rate_pct":56.52173913043478,"oos_2024_profit_factor":1.012518509587113,"oos_2025_profit_factor":0.8087264658393676,"oos_2026_ytd_profit_factor":4.357506738999593},{"model":"Model - 3-100","pf_rank":84,"group_id":5248,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":79,"oos_profit_factor":1.3760407991116388,"oos_net_profit_bps":633.1273277012275,"oos_max_drawdown_pct":-4.175857058744259,"oos_win_rate_pct":45.56962025316456,"oos_2024_profit_factor":1.0316813660988784,"oos_2025_profit_factor":0.6827916254763788,"oos_2026_ytd_profit_factor":3.156044146195712},{"model":"Model - 3-100","pf_rank":85,"group_id":5750,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":146,"oos_profit_factor":1.3741924023422245,"oos_net_profit_bps":1570.0054196571955,"oos_max_drawdown_pct":-6.1454103950219885,"oos_win_rate_pct":50.0,"oos_2024_profit_factor":1.1542332366264694,"oos_2025_profit_factor":2.2510594989868205,"oos_2026_ytd_profit_factor":1.068334525493957},{"model":"Model - 3-100","pf_rank":86,"group_id":5788,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":68,"oos_profit_factor":1.3735225779596087,"oos_net_profit_bps":560.1693367091914,"oos_max_drawdown_pct":-4.509563861716559,"oos_win_rate_pct":45.588235294117645,"oos_2024_profit_factor":1.111781694906376,"oos_2025_profit_factor":0.6078064168038544,"oos_2026_ytd_profit_factor":4.080980362250355},{"model":"Model - 3-100","pf_rank":87,"group_id":5934,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":84,"oos_profit_factor":1.3729817982902,"oos_net_profit_bps":776.4927419739397,"oos_max_drawdown_pct":-3.748126030052612,"oos_win_rate_pct":55.95238095238096,"oos_2024_profit_factor":0.8070789222587871,"oos_2025_profit_factor":1.7820215629480882,"oos_2026_ytd_profit_factor":2.1208038199697565},{"model":"Model - 3-100","pf_rank":88,"group_id":6120,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.2,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":117,"oos_profit_factor":1.3712061116271297,"oos_net_profit_bps":1155.1008735674216,"oos_max_drawdown_pct":-2.9399750500402333,"oos_win_rate_pct":51.28205128205128,"oos_2024_profit_factor":1.582111427885763,"oos_2025_profit_factor":1.5237816881045874,"oos_2026_ytd_profit_factor":1.0313331639691508},{"model":"Model - 3-100","pf_rank":89,"group_id":5668,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.2,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":149,"oos_profit_factor":1.3701890553713203,"oos_net_profit_bps":1201.7569953365096,"oos_max_drawdown_pct":-3.5574181373416613,"oos_win_rate_pct":43.62416107382551,"oos_2024_profit_factor":1.1841874093107412,"oos_2025_profit_factor":1.3887885180683366,"oos_2026_ytd_profit_factor":1.610535759776854},{"model":"Model - 3-100","pf_rank":90,"group_id":5394,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":82,"oos_profit_factor":1.366958599204017,"oos_net_profit_bps":747.3310619737892,"oos_max_drawdown_pct":-4.5003616000732105,"oos_win_rate_pct":54.87804878048781,"oos_2024_profit_factor":0.6890667928979816,"oos_2025_profit_factor":1.998359710229608,"oos_2026_ytd_profit_factor":2.4259974714306294},{"model":"Model - 3-100","pf_rank":91,"group_id":5334,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":6,"oos_trades":104,"oos_profit_factor":1.3667182993966445,"oos_net_profit_bps":842.1565875778044,"oos_max_drawdown_pct":-4.738395910809135,"oos_win_rate_pct":55.76923076923077,"oos_2024_profit_factor":0.7661669181376684,"oos_2025_profit_factor":1.410674471651616,"oos_2026_ytd_profit_factor":2.5995018312924856},{"model":"Model - 3-100","pf_rank":92,"group_id":5738,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.4,"adx_min":20,"adx_max":35,"rsi_mode":"exact","retracement":0.85,"rr":3.0,"pending_bars":3,"oos_trades":67,"oos_profit_factor":1.3664133483386645,"oos_net_profit_bps":561.1544587112224,"oos_max_drawdown_pct":-4.433445410167247,"oos_win_rate_pct":44.776119402985074,"oos_2024_profit_factor":0.7989815459510821,"oos_2025_profit_factor":2.34258467730116,"oos_2026_ytd_profit_factor":1.5909340572090067},{"model":"Model - 3-100","pf_rank":93,"group_id":5868,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.7,"adx_min":18,"adx_max":30,"rsi_mode":"loose","retracement":0.85,"rr":3.0,"pending_bars":6,"oos_trades":74,"oos_profit_factor":1.366003076544738,"oos_net_profit_bps":592.239749253072,"oos_max_drawdown_pct":-3.695464025092021,"oos_win_rate_pct":47.2972972972973,"oos_2024_profit_factor":1.16358073120587,"oos_2025_profit_factor":0.9116036471630864,"oos_2026_ytd_profit_factor":2.633024918786694},{"model":"Model - 3-100","pf_rank":94,"group_id":5584,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.2,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":104,"oos_profit_factor":1.3659447219873768,"oos_net_profit_bps":805.6140773172708,"oos_max_drawdown_pct":-2.695731992370176,"oos_win_rate_pct":53.84615384615385,"oos_2024_profit_factor":1.3835966851457218,"oos_2025_profit_factor":1.0174331143290445,"oos_2026_ytd_profit_factor":1.7541464324370877},{"model":"Model - 3-100","pf_rank":95,"group_id":5154,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":111,"oos_profit_factor":1.365678466966853,"oos_net_profit_bps":884.5435328879005,"oos_max_drawdown_pct":-3.402109620870597,"oos_win_rate_pct":54.95495495495496,"oos_2024_profit_factor":1.1435639574687828,"oos_2025_profit_factor":0.8412385726870459,"oos_2026_ytd_profit_factor":2.9650336694843182},{"model":"Model - 3-100","pf_rank":96,"group_id":5224,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":66,"oos_profit_factor":1.3650741548205223,"oos_net_profit_bps":545.3010847824883,"oos_max_drawdown_pct":-4.304344291341811,"oos_win_rate_pct":54.54545454545454,"oos_2024_profit_factor":0.8354909591659809,"oos_2025_profit_factor":1.107379555232345,"oos_2026_ytd_profit_factor":3.080224924183604},{"model":"Model - 3-100","pf_rank":97,"group_id":5664,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.2,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":173,"oos_profit_factor":1.3641293377381485,"oos_net_profit_bps":1404.283913771625,"oos_max_drawdown_pct":-5.237216596657102,"oos_win_rate_pct":53.75722543352601,"oos_2024_profit_factor":1.0522137289730222,"oos_2025_profit_factor":1.4605289147732805,"oos_2026_ytd_profit_factor":1.790429385448104},{"model":"Model - 3-100","pf_rank":98,"group_id":5300,"symbol":"BTCUSDT","timeframe":"1h","atr_period":14,"impulse_atr":2.5,"adx_min":20,"adx_max":35,"rsi_mode":"none","retracement":0.75,"rr":2.0,"pending_bars":3,"oos_trades":124,"oos_profit_factor":1.36342734511462,"oos_net_profit_bps":1328.2335394484785,"oos_max_drawdown_pct":-6.088845240154583,"oos_win_rate_pct":50.80645161290322,"oos_2024_profit_factor":1.1274274134131792,"oos_2025_profit_factor":2.2262235641135804,"oos_2026_ytd_profit_factor":1.0742768870399453},{"model":"Model - 3-100","pf_rank":99,"group_id":6216,"symbol":"BTCUSDT","timeframe":"1h","atr_period":25,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.82,"rr":3.0,"pending_bars":3,"oos_trades":66,"oos_profit_factor":1.363355699828799,"oos_net_profit_bps":616.6744693016298,"oos_max_drawdown_pct":-2.985638706648952,"oos_win_rate_pct":43.93939393939394,"oos_2024_profit_factor":1.1564861996115858,"oos_2025_profit_factor":1.3613651188898592,"oos_2026_ytd_profit_factor":1.6638995606983424},{"model":"Model - 3-100","pf_rank":100,"group_id":5674,"symbol":"BTCUSDT","timeframe":"1h","atr_period":20,"impulse_atr":2.4,"adx_min":18,"adx_max":30,"rsi_mode":"exact","retracement":0.8,"rr":2.0,"pending_bars":3,"oos_trades":74,"oos_profit_factor":1.3629407680525705,"oos_net_profit_bps":587.8922685053157,"oos_max_drawdown_pct":-3.979299618583165,"oos_win_rate_pct":55.4054054054054,"oos_2024_profit_factor":0.8595116976379112,"oos_2025_profit_factor":1.1890441734876598,"oos_2026_ytd_profit_factor":2.7616286930080927}];
// >>> PASTE YOUR TELEGRAM DETAILS HERE <<<
const TELEGRAM = {
  BOT_TOKEN: 'PASTE_BOTFATHER_TOKEN_HERE',
  CHAT_ID: 'PASTE_TELEGRAM_CHAT_ID_HERE'
};

const M3 = {
  MODEL_NAME: 'Model - 3-100',
  SYMBOL: 'BTCUSDT', INTERVAL: '1h', KLINE_LIMIT: 500,
  FEE_BPS_PER_SIDE: 5, SLIPPAGE_BPS_PER_SIDE: 2,
  MAX_HOLD_BARS: 24, STATE_KEY: 'MODEL_3_100_STATE_V1',
  LAST_TS_KEY: 'MODEL_3_100_LAST_PROCESSED_TS_V1',
  SHEET_TRADES: 'M3_100_TRADES', SHEET_SIGNALS: 'M3_100_SIGNALS',
  SHEET_STATUS: 'M3_100_STATUS', SHEET_CONFIGS: 'M3_100_CONFIGS',
  SPREADSHEET_ID_KEY: 'MODEL_3_100_AUTO_SPREADSHEET_ID_V1',
  ALERTS_PENDING_KEY: 'MODEL_3_100_PENDING_TELEGRAM_ALERTS_V1',
  LAST_ENTRY_ALERT_IMPULSE_KEY: 'MODEL_3_100_LAST_ENTRY_ALERT_IMPULSE_TS_V1'
};

/**
 * Uses the bound spreadsheet if one exists. Otherwise reuses an automatically
 * created spreadsheet, or creates one on first run. The ID is stored internally;
 * the user never has to add a Script Property.
 */
function getEngineSpreadsheet_() {
  const props = PropertiesService.getScriptProperties();
  const active = SpreadsheetApp.getActiveSpreadsheet();
  if (active) {
    props.setProperty(M3.SPREADSHEET_ID_KEY, active.getId());
    return active;
  }
  const savedId = props.getProperty(M3.SPREADSHEET_ID_KEY);
  if (savedId) {
    try { return SpreadsheetApp.openById(savedId); }
    catch (e) { props.deleteProperty(M3.SPREADSHEET_ID_KEY); }
  }
  const created = SpreadsheetApp.create('Model - 3-100 BTCUSDT Paper Engine');
  props.setProperty(M3.SPREADSHEET_ID_KEY, created.getId());
  return created;
}

function getTelegramConfig_() {
  const token = String(TELEGRAM.BOT_TOKEN || '').trim();
  const chat = String(TELEGRAM.CHAT_ID || '').trim();
  if (!token || token === 'PASTE_BOTFATHER_TOKEN_HERE') {
    throw new Error('Paste your BotFather token into TELEGRAM.BOT_TOKEN at the top of this script.');
  }
  if (!chat || chat === 'PASTE_TELEGRAM_CHAT_ID_HERE') {
    throw new Error('Paste your Telegram numeric chat ID into TELEGRAM.CHAT_ID at the top of this script.');
  }
  return {token: token, chat: chat};
}

/** One-click setup: creates sheets, installs a single trigger, tests Telegram, runs engine. */
function startModel3Engine() {
  const tg = getTelegramConfig_();
  const ss = getEngineSpreadsheet_();
  testTelegramConnection();
  setupModel3();
  const firstPoll = runModel3Engine();
  if (firstPoll && firstPoll.ok === false) {
    const paused = 'Setup complete; five-minute trigger installed, but the first market-data poll was safely paused. Check M3_100_STATUS. Spreadsheet: ' + ss.getUrl();
    Logger.log(paused);
    return paused;
  }
  Logger.log('Model - 3-100 started. Spreadsheet: ' + ss.getUrl());
  return 'Model - 3-100 started. Spreadsheet: ' + ss.getUrl();
}

function setupModel3() {
  const ss = getEngineSpreadsheet_();
  ensureSheet_(ss, M3.SHEET_TRADES, ['model','config_id','symbol','timeframe','side','entry_time_utc','exit_time_utc','entry','exit','stop','target','exit_reason','gross_bps','fees_bps','funding_cost_bps','net_bps','net_R']);
  ensureSheet_(ss, M3.SHEET_SIGNALS, ['paper_fill_time_utc','model','config_id','research_rank','side','paper_entry_price','stop','target','rr','impulse_atr','adx_min','adx_max','retracement','rsi_mode','status']);
  ensureSheet_(ss, M3.SHEET_STATUS, ['updated_utc','model','configs','open_positions','pending_orders','closed_trades','wins','losses','win_rate_pct','profit_factor','net_bps','last_processed_candle_utc','engine_note']);
  ensureSheet_(ss, M3.SHEET_CONFIGS, ['model','config_id','research_rank','group_id','symbol','timeframe','atr_period','impulse_atr','adx_min','adx_max','rsi_mode','retracement','rr','pending_bars','oos_trades','oos_profit_factor','oos_net_profit_bps','oos_max_drawdown_pct','oos_win_rate_pct','oos_2024_pf','oos_2025_pf','oos_2026_ytd_pf']);
  const cfgSheet = ss.getSheetByName(M3.SHEET_CONFIGS);
  const expectedRows = M3_CONFIGS.map(c => [M3.MODEL_NAME,cfgKey_(c),c.pf_rank,c.group_id,c.symbol,c.timeframe,c.atr_period,c.impulse_atr,c.adx_min,c.adx_max,c.rsi_mode,c.retracement,c.rr,c.pending_bars,c.oos_trades,c.oos_profit_factor,c.oos_net_profit_bps,c.oos_max_drawdown_pct,c.oos_win_rate_pct,c.oos_2024_profit_factor,c.oos_2025_profit_factor,c.oos_2026_ytd_profit_factor]);
  // Keep the embedded ranked Top-100 list authoritative; refresh this engine's config sheet.
  if (cfgSheet.getLastRow() > 1) cfgSheet.getRange(2,1,cfgSheet.getLastRow()-1,cfgSheet.getLastColumn()).clearContent();
  if (expectedRows.length) cfgSheet.getRange(2,1,expectedRows.length,expectedRows[0].length).setValues(expectedRows);
  const props=PropertiesService.getScriptProperties();
  if (!props.getProperty(M3.STATE_KEY)) props.setProperty(M3.STATE_KEY, JSON.stringify(initialStates_()));
  // Replace only this engine's polling trigger; no separate 3A/3B/3C triggers.
  ScriptApp.getProjectTriggers().forEach(t => { if (t.getHandlerFunction()==='runModel3Engine') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('runModel3Engine').timeBased().everyMinutes(5).create();
  writeStatusNote_('Setup complete. One model, 100 ranked configurations; completed 1-hour candles; paper mode only.');
  return ss;
}

function runModel3Engine() {
  const lock=LockService.getScriptLock();
  if (!lock.tryLock(20000)) return;
  try {
    const now=Date.now();
    const bars=fetchClosedKlines_();
    if (bars.length < 80) throw new Error('Insufficient closed 1h candles: '+bars.length);
    const funding=fetchRecentFunding_();
    const props=PropertiesService.getScriptProperties();
    // Retry any Telegram notification that failed on a previous polling cycle.
    const pendingAlertText=props.getProperty(M3.ALERTS_PENDING_KEY);
    if (pendingAlertText) {
      const pendingAlert=JSON.parse(pendingAlertText);
      sendTelegramDigest_(pendingAlert.alerts, pendingAlert.ts);
      props.deleteProperty(M3.ALERTS_PENDING_KEY);
    }
    let states=JSON.parse(props.getProperty(M3.STATE_KEY)||'{}');
    if (!Object.keys(states).length) states=initialStates_();
    let lastTs=Number(props.getProperty(M3.LAST_TS_KEY)||0);
    if (!lastTs) {
      // Warm start: process the latest closed bar only; don't fabricate old alerts/trades.
      lastTs=bars[bars.length-2].time;
      props.setProperty(M3.LAST_TS_KEY,String(lastTs));
    }
    if (lastTs < bars[0].time) throw new Error('Stored checkpoint is older than the 500-candle recovery window. Reset paper state or restore a longer data history; refusing to invent missed fills.');
    const newBars=bars.filter(b=>b.time>lastTs);
    if (!newBars.length) { updateDashboard_(states,bars[bars.length-1].time,'No new closed candle.'); return; }
    const indicatorsByAtr={};
    const tradeRows=[], signalRows=[], exitAlerts=[], entryAlertsByImpulse={};
    let processedTs=lastTs;
    // Indicators are calculated on the full recent closed-candle history to preserve warm-up.
    M3_CONFIGS.forEach(cfg=>{
        const model=M3.MODEL_NAME;
        const id=cfgKey_(cfg);
        if (!states[id]) states[id]=emptyState_();
        if (!indicatorsByAtr[cfg.atr_period]) indicatorsByAtr[cfg.atr_period]=calculateIndicators_(bars,cfg.atr_period);
        const ind=indicatorsByAtr[cfg.atr_period];
        for (let j=0;j<newBars.length;j++) {
          const bar=newBars[j];
          const i=bars.findIndex(x=>x.time===bar.time);
          if (i<1) continue;
          const sig=impulseSignal_(bars[i-1],ind,i-1,cfg);
          const result=advanceConfig_(states[id],bars,i,sig,cfg,funding);
          if (result.trade) {
            tradeRows.push(result.trade);
            exitAlerts.push({type:'EXIT',model:model,id:result.trade[1],side:result.trade[4],entry:result.trade[7],exit:result.trade[8],reason:result.trade[11],netBps:Number(result.trade[15])});
          }
          if (result.setup) {
            // Alert on the first accepted strong-candle setup; no multi-config confirmation required.
            addEntryAlertForImpulse_(entryAlertsByImpulse,result.setup,model,id,cfg);
          }
          if (result.signal) {
            const s=result.signal;
            signalRows.push([new Date(s.time),model,id,cfg.pf_rank,s.side===1?'LONG':'SHORT',s.level,s.stop,s.target,cfg.rr,cfg.impulse_atr,cfg.adx_min,cfg.adx_max,cfg.retracement,cfg.rsi_mode,'PAPER_FILLED']);
          }
        }
    });
    if (tradeRows.length) appendRows_(M3.SHEET_TRADES,tradeRows);
    if (signalRows.length) appendRows_(M3.SHEET_SIGNALS,signalRows);
    processedTs=newBars[newBars.length-1].time;
    // One ENTRY notification per originating strong-candle timestamp across all
    // 100 configurations. A single accepted setup is enough; confirmations are not required.
    // The gate is keyed to the strong-candle timestamp, so only a later strong candle can alert again.
    const lastEntryAlertImpulseTs=Number(props.getProperty(M3.LAST_ENTRY_ALERT_IMPULSE_KEY)||0);
    const freshEntryAlerts=buildFreshEntryAlerts_(entryAlertsByImpulse,lastEntryAlertImpulseTs);
    const alerts=exitAlerts.concat(freshEntryAlerts);
    // Persist unsent alerts before advancing the checkpoint. If Telegram is
    // temporarily unavailable, the next poll retries this exact notification.
    if (alerts.length) props.setProperty(M3.ALERTS_PENDING_KEY, JSON.stringify({alerts:alerts,ts:processedTs}));
    if (freshEntryAlerts.length) {
      const newestImpulseTs=Math.max.apply(null,freshEntryAlerts.map(x=>x.impulseTs));
      props.setProperty(M3.LAST_ENTRY_ALERT_IMPULSE_KEY,String(newestImpulseTs));
    }
    props.setProperty(M3.STATE_KEY,JSON.stringify(states));
    props.setProperty(M3.LAST_TS_KEY,String(processedTs));
    updateDashboard_(states,processedTs,'Processed '+newBars.length+' newly closed candle(s); paper mode only.');
    if (alerts.length) {
      sendTelegramDigest_(alerts,processedTs);
      props.deleteProperty(M3.ALERTS_PENDING_KEY);
    }
  } catch(err) {
    const message = 'ENGINE PAUSED THIS CYCLE — no new signals emitted: ' + String(err && err.message ? err.message : err);
    try { writeStatusNote_(message); } catch(noteErr) { Logger.log('Could not write status note: '+noteErr); }
    Logger.log(message);
    // Do not advance the candle checkpoint on provider/data errors. The next
    // 5-minute trigger retries; the trigger itself remains installed.
    return {ok:false, reason:message};
  } finally { lock.releaseLock(); }
}

/** Aggregate setup triggers from all 100 configs by originating strong-candle timestamp. */
function addEntryAlertForImpulse_(groups,s,model,id,cfg) {
  const impulseTs=Number(s.signalTime||s.time);
  const key=String(impulseTs);
  if (!groups[key]) groups[key]={type:'ENTRY_SETUP',impulseTs:impulseTs,model:M3.MODEL_NAME,id:id,rank:cfg.pf_rank,side:s.side,
    level:s.level,stop:s.stop,target:s.target,rr:cfg.rr,configCount:0,configIds:[]};
  const g=groups[key];
  g.configCount++;
  g.configIds.push(id);
  // Any one setup is sufficient. If several configs trigger together, display the best PF-ranked one.
  if (cfg.pf_rank < g.rank) { g.id=id; g.rank=cfg.pf_rank; g.level=s.level; g.stop=s.stop; g.target=s.target; g.rr=cfg.rr; }
}

/** One setup alert per strong-candle timestamp; later candle opens the next alert opportunity. */
function buildFreshEntryAlerts_(groups,lastAlertedImpulseTs) {
  return Object.keys(groups).map(k=>groups[k])
    .filter(x=>Number(x.impulseTs)>Number(lastAlertedImpulseTs||0))
    .sort((a,b)=>a.impulseTs-b.impulseTs);
}

function initialStates_() {
  const s={}; M3_CONFIGS.forEach(c=>s[cfgKey_(c)]=emptyState_()); return s;
}
function emptyState_() { return {side:0,entry:0,stop:0,target:0,risk:0,entryTime:0,heldBars:0,pending:null}; }
function cfgKey_(cfg) { return 'M3_100_R'+String(cfg.pf_rank).padStart(3,'0'); }

/** Binance's documented USD-M Futures REST base URL. Do not substitute
 * Spot endpoints or undocumented mirrors for futures candles/funding data.
 */
const M3_FUTURES_HOSTS = ['https://fapi.binance.com'];

function fetchBinanceJson_(path, query, label, validator) {
  const errors = [];
  for (let i = 0; i < M3_FUTURES_HOSTS.length; i++) {
    const url = M3_FUTURES_HOSTS[i] + path + '?' + query;
    try {
      const response = UrlFetchApp.fetch(url, {
        muteHttpExceptions: true,
        followRedirects: true,
        headers: {'Accept': 'application/json'}
      });
      const code = response.getResponseCode();
      const body = response.getContentText() || '';
      if (code < 200 || code >= 300) {
        errors.push(M3_FUTURES_HOSTS[i] + ' HTTP ' + code + ': ' + body.slice(0, 220).replace(/\s+/g, ' '));
        continue;
      }
      let data;
      try { data = JSON.parse(body); }
      catch (e) {
        errors.push(M3_FUTURES_HOSTS[i] + ' returned invalid JSON: ' + body.slice(0, 180));
        continue;
      }
      if (!validator(data)) {
        errors.push(M3_FUTURES_HOSTS[i] + ' returned an unexpected ' + label + ' payload');
        continue;
      }
      return data;
    } catch (e) {
      errors.push(M3_FUTURES_HOSTS[i] + ' fetch exception: ' + String(e).slice(0, 180));
    }
  }
  throw new Error('Binance ' + label + ' unavailable on all ' + M3_FUTURES_HOSTS.length +
    ' official USD-M Futures hosts. No signals processed. ' + errors.join(' | '));
}

function fetchClosedKlines_() {
  const query = 'symbol=' + encodeURIComponent(M3.SYMBOL) + '&interval=' +
    encodeURIComponent(M3.INTERVAL) + '&limit=' + M3.KLINE_LIMIT;
  const data = fetchBinanceJson_('/fapi/v1/klines', query, 'klines', function(x) {
    return Array.isArray(x) && x.length >= 80 && x.every(function(k) {
      return Array.isArray(k) && k.length >= 7 &&
        Number.isFinite(Number(k[0])) && Number.isFinite(Number(k[6])) &&
        [1,2,3,4,5].every(function(j) { return Number.isFinite(Number(k[j])); }) &&
        Number(k[2]) >= Number(k[3]) &&
        Number(k[2]) >= Math.max(Number(k[1]),Number(k[4])) &&
        Number(k[3]) <= Math.min(Number(k[1]),Number(k[4])) && Number(k[5]) >= 0;
    });
  });
  const now = Date.now();
  const bars = data.filter(function(x) { return Number(x[6]) < now; }).map(function(x) {
    const b = {time: Number(x[0]) + 3600000, open: Number(x[1]), high: Number(x[2]),
      low: Number(x[3]), close: Number(x[4]), volume: Number(x[5])};
    if (!(b.high >= b.low && b.high >= Math.max(b.open,b.close) &&
          b.low <= Math.min(b.open,b.close) && b.volume >= 0)) {
      throw new Error('Binance returned invalid OHLCV candle at ' + new Date(Number(x[0])).toISOString());
    }
    return b;
  }).sort(function(a,b) { return a.time-b.time; });
  const unique = [];
  bars.forEach(function(b) {
    if (!unique.length || unique[unique.length-1].time !== b.time) unique.push(b);
  });
  if (unique.length < 80) throw new Error('Only ' + unique.length + ' valid closed candles received; refusing to evaluate.');
  if (now - unique[unique.length-1].time > 2*3600000) {
    throw new Error('Latest closed Binance candle is stale (' + Math.round((now-unique[unique.length-1].time)/60000) +
      ' minutes old); refusing to emit signals.');
  }
  for (let i=1; i<unique.length; i++) {
    if (unique[i].time - unique[i-1].time !== 3600000) {
      throw new Error('Gap in 1-hour Binance candles between ' + new Date(unique[i-1].time).toISOString() +
        ' and ' + new Date(unique[i].time).toISOString() + '; refusing to process incomplete history.');
    }
  }
  return unique;
}

function fetchRecentFunding_() {
  const query = 'symbol=' + encodeURIComponent(M3.SYMBOL) + '&limit=1000';
  const data = fetchBinanceJson_('/fapi/v1/fundingRate', query, 'funding rates', function(x) {
    return Array.isArray(x) && x.every(function(f) {
      return f && Number.isFinite(Number(f.fundingTime)) && Number.isFinite(Number(f.fundingRate));
    });
  });
  return data.map(function(x) { return {time:Number(x.fundingTime), rate:Number(x.fundingRate)}; });
}

// Matches the research runner's Wilder smoothing convention.
function wilder_(values,n) {
  const out=Array(values.length).fill(null); let acc=null,count=0;
  for (let i=0;i<values.length;i++) {
    const x=values[i]; if (x===null || !Number.isFinite(x)) continue;
    if (acc===null) { acc=x; count=1; }
    else { acc=(1-1/n)*acc+x/n; count++; }
    if (count>=n) out[i]=acc;
  }
  return out;
}
function calculateIndicators_(bars,atrN) {
  const n=bars.length, tr=Array(n).fill(null), pdm=Array(n).fill(0), mdm=Array(n).fill(0), delta=Array(n).fill(null);
  for (let i=1;i<n;i++) {
    const b=bars[i],p=bars[i-1]; tr[i]=Math.max(b.high-b.low,Math.abs(b.high-p.close),Math.abs(b.low-p.close));
    const up=b.high-p.high,down=p.low-b.low; pdm[i]=(up>down&&up>0)?up:0; mdm[i]=(down>up&&down>0)?down:0; delta[i]=b.close-p.close;
  }
  const atrRaw=wilder_(tr,atrN), atrPrior=atrRaw.map((v,i)=>i?atrRaw[i-1]:null);
  const ag=wilder_(delta.map(x=>x===null?null:Math.max(x,0)),14);
  const al=wilder_(delta.map(x=>x===null?null:Math.max(-x,0)),14);
  const rsi=ag.map((a,i)=>{
    const b=al[i]; if(a===null||b===null) return null; if(b===0) return 100; const rs=a/b; return 100-100/(1+rs);
  });
  const atr14=wilder_(tr,14), p=wilder_(pdm,14), m=wilder_(mdm,14);
  const dx=atr14.map((a,i)=>{
    if(a===null||p[i]===null||m[i]===null||a===0) return null;
    const pdi=100*p[i]/a,mdi=100*m[i]/a,den=pdi+mdi; return den===0?null:100*Math.abs(pdi-mdi)/den;
  });
  const adx=wilder_(dx,14);
  return {atrPrior:atrPrior,rsi:rsi,adx:adx};
}
function impulseSignal_(bar,ind,i,cfg) {
  const atr=ind.atrPrior[i],adx=ind.adx[i],rsi=ind.rsi[i];
  if(atr===null||adx===null||!Number.isFinite(atr)||atr<=0||adx<cfg.adx_min||adx>cfg.adx_max) return 0;
  const dir=bar.close>bar.open?1:(bar.close<bar.open?-1:0),range=bar.high-bar.low;
  if(!dir||range<cfg.impulse_atr*atr) return 0;
  if(cfg.rsi_mode==='exact') {
    if(dir===1 && !(rsi!==null&&rsi>=50&&rsi<=70)) return 0;
    if(dir===-1 && !(rsi!==null&&rsi>=30&&rsi<=50)) return 0;
  } else if(cfg.rsi_mode==='loose') {
    if(dir===1 && !(rsi!==null&&rsi>=50&&rsi<=75)) return 0;
    if(dir===-1 && !(rsi!==null&&rsi>=25&&rsi<=50)) return 0;
  } else if(cfg.rsi_mode!=='none') throw new Error('Unknown RSI mode '+cfg.rsi_mode);
  return dir;
}
function advanceConfig_(st,bars,i,sig,cfg,funding) {
  const b=bars[i],ts=b.time,prev=bars[i-1]; let trade=null,newSignal=null,newSetup=null;
  // First manage an existing position; ambiguous same-candle stop/target resolves stop-first.
  if(st.side) {
    st.heldBars++;
    const sh=st.side===1?b.low<=st.stop:b.high>=st.stop;
    const th=st.side===1?b.high>=st.target:b.low<=st.target;
    if(sh||th||st.heldBars>=M3.MAX_HOLD_BARS) {
      let px,why;
      if(sh) { px=(st.side===1&&b.open<st.stop)||(st.side===-1&&b.open>st.stop)?b.open:st.stop; why='STOP'; }
      else if(th) { px=st.target; why='TARGET'; }
      else { px=b.close; why='TIME'; }
      trade=closeState_(st,px,ts,why,cfg,funding);
    }
  }
  if(!st.side && !st.pending && sig && prev.time>0) {
    const span=prev.high-prev.low,level=sig===1?prev.high-cfg.retracement*span:prev.low+cfg.retracement*span;
    const stop=sig===1?prev.low:prev.high;
    st.pending={side:sig,level:level,stop:stop,signalTime:prev.time,signalIndex:i-1};
    const plannedRisk=Math.abs(level-stop);
    if(plannedRisk>0) newSetup={time:ts,signalTime:prev.time,side:sig,level:level,stop:stop,target:level+sig*cfg.rr*plannedRisk};
  }
  if(!st.side && st.pending) {
    const p=st.pending,age=i-p.signalIndex;
    if(age>cfg.pending_bars) st.pending=null;
    else {
      const invalid=p.side===1?b.open<=p.stop:b.open>=p.stop;
      if(invalid) st.pending=null;
      else {
        const touched=p.side===1?b.low<=p.level:b.high>=p.level;
        if(touched) {
          const raw=p.side===1?Math.min(b.open,p.level):Math.max(b.open,p.level);
          const fill=raw*(1+p.side*M3.SLIPPAGE_BPS_PER_SIDE/10000),risk=Math.abs(fill-p.stop);
          if(risk>0 && ((p.side===1&&p.stop<fill)||(p.side===-1&&p.stop>fill))) {
            st.side=p.side; st.entry=fill; st.stop=p.stop; st.risk=risk; st.target=fill+p.side*cfg.rr*risk; st.entryTime=ts; st.heldBars=0;
            newSignal={time:ts,signalTime:p.signalTime,side:p.side,level:fill,stop:st.stop,target:st.target};
            const sh=p.side===1?b.low<=st.stop:b.high>=st.stop,th=p.side===1?b.high>=st.target:b.low<=st.target;
            if(sh||th) {
              const px=sh?((p.side===1&&b.open<st.stop)||(p.side===-1&&b.open>st.stop)?b.open:st.stop):st.target;
              trade=closeState_(st,px,ts,sh?'STOP':'TARGET',cfg,funding);
            }
          }
          st.pending=null;
        }
      }
    }
  }
  return {trade:trade,signal:newSignal,setup:newSetup};
}
function closeState_(st,rawExit,exitTime,reason,cfg,funding) {
  const side=st.side,exit=rawExit*(1-side*M3.SLIPPAGE_BPS_PER_SIDE/10000);
  const gross=side*(exit-st.entry)/st.entry;
  let fundingCost=0;
  funding.forEach(f=>{if(f.time>=st.entryTime && f.time<=exitTime) fundingCost+=f.rate*side;});
  const net=gross-2*M3.FEE_BPS_PER_SIDE/10000-fundingCost;
  const row=[M3.MODEL_NAME,cfgKey_(cfg),cfg.symbol,cfg.timeframe,side===1?'LONG':'SHORT',new Date(st.entryTime),new Date(exitTime),st.entry,exit,st.stop,st.target,reason,gross*10000,2*M3.FEE_BPS_PER_SIDE,fundingCost*10000,net*10000,st.risk?net/(st.risk/st.entry):0];
  Object.assign(st,emptyState_());
  return row;
}

function ensureSheet_(ss,name,headers) {
  let sh=ss.getSheetByName(name); if(!sh) sh=ss.insertSheet(name);
  if(sh.getLastRow()===0) sh.getRange(1,1,1,headers.length).setValues([headers]);
  else sh.getRange(1,1,1,headers.length).setValues([headers]);
  return sh;
}
function appendRows_(name,rows) {
  const sh=getEngineSpreadsheet_().getSheetByName(name);
  if(rows.length) sh.getRange(sh.getLastRow()+1,1,rows.length,rows[0].length).setValues(rows);
}
function updateDashboard_(states,lastTs,note) {
  const ss=getEngineSpreadsheet_(),sh=ss.getSheetByName(M3.SHEET_STATUS);
  const trades=ss.getSheetByName(M3.SHEET_TRADES),data=trades.getLastRow()>1?trades.getRange(2,1,trades.getLastRow()-1,17).getValues():[];
  const ids=M3_CONFIGS.map(c=>cfgKey_(c));
  const wins=data.filter(r=>Number(r[15])>0),loss=data.filter(r=>Number(r[15])<=0);
  const gp=wins.reduce((a,r)=>a+Number(r[15]),0),gl=-loss.reduce((a,r)=>a+Number(r[15]),0);
  const open=ids.filter(id=>states[id]&&states[id].side).length,pending=ids.filter(id=>states[id]&&states[id].pending).length;
  const row=[new Date(),M3.MODEL_NAME,M3_CONFIGS.length,open,pending,data.length,wins.length,loss.length,data.length?100*wins.length/data.length:0,gl?gp/gl:'',data.reduce((a,r)=>a+Number(r[15]),0),new Date(lastTs),note];
  sh.clearContents();
  sh.getRange(1,1,1,13).setValues([['updated_utc','model','configs','open_positions','pending_orders','closed_trades','wins','losses','win_rate_pct','profit_factor','net_bps','last_processed_candle_utc','engine_note']]);
  sh.getRange(2,1,1,13).setValues([row]);
}

function writeStatusNote_(note) {
  const ss=getEngineSpreadsheet_(); let sh=ss.getSheetByName(M3.SHEET_STATUS);
  if(!sh) sh=ss.insertSheet(M3.SHEET_STATUS);
  sh.getRange(1,14).setValue('Last update: '+new Date().toISOString()+' | '+note);
}
function sendTelegramDigest_(alerts,ts) {
  const tg=getTelegramConfig_(),token=tg.token,chat=tg.chat;
  const entries=alerts.filter(x=>x.type==='ENTRY_SETUP'),exits=alerts.filter(x=>x.type==='EXIT');
  const lines=['MODEL - 3-100 — PAPER TRADING ALERT','BTCUSDT · 1H · '+new Date(ts).toISOString(),
    '100 PF-ranked configurations · One setup alert per originating strong candle.',
    'One configuration trigger is sufficient; no multi-configuration confirmation is required.',
    'Alert is a pending retracement setup, not a confirmed paper fill.',
    'Paper signals only — no exchange orders placed.'];
  entries.slice(0,20).forEach(x=>lines.push('STRONG-CANDLE SETUP '+(x.side===1?'LONG':'SHORT')+' | pending limit '+x.level.toFixed(2)+' | SL '+x.stop.toFixed(2)+' | planned TP '+x.target.toFixed(2)+' | RR '+x.rr+' | first config '+x.id+' (PF rank '+x.rank+') | '+(x.configCount||1)+' config trigger(s) on this candle | strong candle '+new Date(x.impulseTs||ts).toISOString()));
  if(entries.length>20) lines.push('... '+(entries.length-20)+' more strong-candle entries; see M3_100_SIGNALS.');
  exits.slice(0,20).forEach(x=>lines.push('EXIT '+x.id+' '+x.side+' @ '+Number(x.exit).toFixed(2)+' | '+x.reason+' | net '+Number(x.netBps).toFixed(1)+' bps'));
  if(exits.length>20) lines.push('... '+(exits.length-20)+' more exits; see M3_100_TRADES.');
  const url='https://api.telegram.org/bot'+token+'/sendMessage';
  const response=UrlFetchApp.fetch(url,{method:'post',contentType:'application/json',payload:JSON.stringify({chat_id:chat,text:lines.join('\n')}),muteHttpExceptions:true});
  const code=response.getResponseCode(),body=response.getContentText();
  if(code<200||code>=300) throw new Error('Telegram sendMessage failed ('+code+'): '+body);
  const parsed=JSON.parse(body);
  if(!parsed.ok) throw new Error('Telegram rejected message: '+body);
}

// Sends a Telegram test message and includes the engine spreadsheet link.
function testTelegramConnection() {
  const tg=getTelegramConfig_();
  const response=UrlFetchApp.fetch('https://api.telegram.org/bot'+tg.token+'/sendMessage',{
    method:'post', contentType:'application/json',
    payload:JSON.stringify({chat_id:tg.chat,text:'Model - 3-100 paper engine: Telegram connection test successful. 100 configurations, one setup alert per strong candle. Paper signals only; no exchange orders.\nEngine log sheet: '+getEngineSpreadsheet_().getUrl()}),
    muteHttpExceptions:true
  });
  const body=response.getContentText(),code=response.getResponseCode();
  let parsed;
  try { parsed=JSON.parse(body); } catch(e) { throw new Error('Telegram returned invalid JSON ('+code+'): '+body); }
  if(code<200||code>=300||!parsed.ok) throw new Error('Telegram test failed ('+code+'): '+body);
  return 'Telegram test message sent successfully.';
}

// Optional: clears only this engine's paper state and logs; does not touch other sheets.
function resetModel3PaperState() {
  const props=PropertiesService.getScriptProperties(); [M3.STATE_KEY,M3.LAST_TS_KEY,M3.LAST_ENTRY_ALERT_IMPULSE_KEY,M3.ALERTS_PENDING_KEY].forEach(k=>props.deleteProperty(k));
  const ss=getEngineSpreadsheet_(); [M3.SHEET_TRADES,M3.SHEET_SIGNALS].forEach(n=>{const sh=ss.getSheetByName(n);if(sh&&sh.getLastRow()>1)sh.getRange(2,1,sh.getLastRow()-1,sh.getLastColumn()).clearContent();});
  setupModel3();
}

/** Returns the automatically selected/created spreadsheet URL. */
function showModel3SpreadsheetUrl() {
  const ss=getEngineSpreadsheet_();
  Logger.log(ss.getUrl());
  return ss.getUrl();
}