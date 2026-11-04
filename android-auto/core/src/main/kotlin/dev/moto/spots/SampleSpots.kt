package dev.moto.spots

/**
 * 動作確認用のダミーデータ(東京駅周辺)。実在の店舗・施設ではない。
 * 本番では SpotRepository を実データ源で実装して置き換える。
 */
object SampleSpots : SpotRepository {

    /** 位置情報の権限がないときに使う検索地点(東京駅付近)。 */
    val DEFAULT_ORIGIN = GeoPoint(35.6812, 139.7671)

    private val spots = listOf(
        Spot("fuel-1", "サンプル給油所 丸の内", SpotCategory.FUEL, GeoPoint(35.6840, 139.7640), "東京都千代田区(サンプル)", "ハイオク・レギュラー"),
        Spot("fuel-2", "サンプル給油所 八重洲", SpotCategory.FUEL, GeoPoint(35.6790, 139.7710), "東京都中央区(サンプル)", "セルフ"),
        Spot("fuel-3", "サンプル給油所 日本橋", SpotCategory.FUEL, GeoPoint(35.6860, 139.7750), "東京都中央区(サンプル)"),
        Spot("fuel-4", "サンプル給油所 神田", SpotCategory.FUEL, GeoPoint(35.6920, 139.7700), "東京都千代田区(サンプル)", "24 時間"),
        Spot("park-1", "サンプル二輪駐車場 大手町", SpotCategory.MOTO_PARKING, GeoPoint(35.6860, 139.7630), "東京都千代田区(サンプル)", "大型可"),
        Spot("park-2", "サンプル二輪駐車場 京橋", SpotCategory.MOTO_PARKING, GeoPoint(35.6770, 139.7700), "東京都中央区(サンプル)", "125cc 以下"),
        Spot("park-3", "サンプル二輪駐車場 有楽町", SpotCategory.MOTO_PARKING, GeoPoint(35.6750, 139.7630), "東京都千代田区(サンプル)"),
        Spot("rest-1", "サンプル休憩所 皇居外苑", SpotCategory.REST, GeoPoint(35.6800, 139.7580), "東京都千代田区(サンプル)", "ベンチあり"),
        Spot("rest-2", "サンプル休憩所 隅田川", SpotCategory.REST, GeoPoint(35.6820, 139.7900), "東京都中央区(サンプル)", "自販機あり"),
    )

    override fun all(): List<Spot> = spots
}
