plugins {
    id("com.android.application")
}

val hearthUrl = (project.findProperty("hearthUrl") as String?) ?: "https://example.invalid"

android {
    namespace = "com.hacktx.mothertongue.hearth"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.hacktx.mothertongue.hearth"
        minSdk = 28
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "HEARTH_URL", "\"$hearthUrl\"")
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
