package com.wzwroot.manager.ui.component

import androidx.compose.runtime.Composable
import com.wzwroot.manager.Natives
import com.wzwroot.manager.ksuApp

@Composable
fun KsuIsValid(
    content: @Composable () -> Unit
) {
    val isManager = Natives.isManager
    val ksuVersion = if (isManager) Natives.version else null

    if (ksuVersion != null) {
        content()
    }
}