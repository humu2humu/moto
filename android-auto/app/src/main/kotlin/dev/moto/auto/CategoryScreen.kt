package dev.moto.auto

import androidx.car.app.CarContext
import androidx.car.app.Screen
import androidx.car.app.model.Action
import androidx.car.app.model.ItemList
import androidx.car.app.model.ListTemplate
import androidx.car.app.model.Row
import androidx.car.app.model.Template
import dev.moto.spots.SpotCategory

/** 最初の画面: 探したいスポットの種類を選ぶ。 */
class CategoryScreen(carContext: CarContext) : Screen(carContext) {

    override fun onGetTemplate(): Template {
        val items = ItemList.Builder()
        for (category in SpotCategory.entries) {
            items.addItem(
                Row.Builder()
                    .setTitle(category.label)
                    .setOnClickListener { screenManager.push(SpotListScreen(carContext, category)) }
                    .build(),
            )
        }
        return ListTemplate.Builder()
            .setTitle(carContext.getString(R.string.app_name))
            .setHeaderAction(Action.APP_ICON)
            .setSingleList(items.build())
            .build()
    }
}
