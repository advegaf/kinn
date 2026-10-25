import SwiftUI

/// 02 the entry: the story film fading into night, the date, her words in English, and her voice.
/// The film and the lit paragraph follow the narration, one scene per beat.
struct EntryView: View {
    var message: Message
    var close: () -> Void
    var writeBack: () -> Void
    private let scenes: [StoryScene]

    @Environment(AppSession.self) private var session
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    init(message: Message, close: @escaping () -> Void, writeBack: @escaping () -> Void) {
        self.message = message
        self.close = close
        self.writeBack = writeBack
        scenes = message.story?.timedScenes(translation: message.translation) ?? []
    }

    private var translatedKey: String { "t-\(message.id)" }
    private var originalKey: String { "o-\(message.id)" }

    #if DEBUG
    /// Screenshot aid: `-seekFraction 0.5` holds the entry at that point of the narration, silent.
    private static let simulated: Double? = UserDefaults.standard.object(forKey: "seekFraction") == nil
        ? nil : UserDefaults.standard.double(forKey: "seekFraction")
    #else
    private static let simulated: Double? = nil
    #endif

    private var playingTranslation: Bool {
        session.player.isPlaying && session.player.currentKey == translatedKey
    }

    /// One clock for the film, the lit beat and the track.
    private var progress: Double {
        Self.simulated ?? (playingTranslation ? session.player.progress : 0)
    }

    private var following: Bool { Self.simulated != nil || playingTranslation }

    private var sceneIndex: Int {
        following && !scenes.isEmpty ? StoryScene.index(in: scenes, at: progress) : 0
    }

    /// The lit beat. Nil when nothing plays, so the whole story reads at full strength.
    private var beatIndex: Int? { following && hasBeats ? sceneIndex : nil }

    private var hasBeats: Bool { !scenes.isEmpty && scenes.allSatisfy { $0.textEn != nil } }

    /// Where a beat settles when the page follows the voice: a little below the middle, clear of the film.
    private let beatAnchor = UnitPoint(x: 0.5, y: 0.6)

    var body: some View {
        ZStack(alignment: .top) {
            NightCanvas()
            film
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        Color.clear.frame(height: 236).id("top")
                        dayHead
                        Text(Almanac.titleEn(message))
                            .font(.serif(34, relativeTo: .title))
                            .tracking(-0.5)
                            .foregroundStyle(Color.cream)
                            .padding(.top, 2)
                        Text(Almanac.titleEs(message))
                            .font(.serifItalic(19))
                            .foregroundStyle(Color.fog)
                            .padding(.top, 6)
                        prose
                            .padding(.top, 18)
                    }
                    .padding(.horizontal, 30)
                    .padding(.bottom, 32)
                }
                .scrollIndicators(.hidden)
                .ignoresSafeArea(edges: .top)
                .mask {
                    // The prose slips under the film instead of sliding across the picture.
                    VStack(spacing: 0) {
                        LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: .clear, location: 0.74),
                                               .init(color: .black, location: 1)], startPoint: .top, endPoint: .bottom)
                            .frame(height: 250)
                        Color.black
                        LinearGradient(colors: [.black, .clear], startPoint: .top, endPoint: .bottom)
                            .frame(height: 20)
                    }
                    .ignoresSafeArea(edges: .top)
                }
                .onChange(of: beatIndex) { _, beat in
                    guard let beat else { return }
                    withAnimation(reduceMotion ? nil : .easeInOut(duration: 1.4)) {
                        // The first beat sits under the date, so it keeps the page at its head.
                        if beat == 0 { proxy.scrollTo("top", anchor: .top) } else { proxy.scrollTo(beat, anchor: beatAnchor) }
                    }
                }
                .task {
                    // Opening mid story (a seek, or the screenshot aid): start with the lit beat in view.
                    guard let beat = beatIndex, beat > 0 else { return }
                    try? await Task.sleep(for: .milliseconds(80))
                    proxy.scrollTo(beat, anchor: beatAnchor)
                }
                }
                track
                    .padding(.horizontal, 30)
                    .padding(.top, 8)
                foot
                    .padding(.horizontal, 30)
                    .padding(.top, 30)
                    .padding(.bottom, 12)
            }
            Vignette()
            Button("Close") {
                session.player.stop()
                close()
            }
            .tinyCaps(.cream.opacity(0.85))
            .shadow(color: .black.opacity(0.6), radius: 8)
            .buttonStyle(PressStyle())
            .frame(minWidth: 44, minHeight: 44)
            .contentShape(.rect)
            .frame(maxWidth: .infinity, alignment: .trailing)
            .padding(.trailing, 22)
            .padding(.top, 6)
        }
        .task(id: message.id) {
            session.markHeard(message.id)
            guard Self.simulated == nil else { return }
            if let src = session.translatedSource(message) { session.player.play(src, key: translatedKey) }
        }
        .onDisappear { session.player.stop() }
    }

    @ViewBuilder private var film: some View {
        ZStack {
            Color.night
            filmMedia
                .id(sceneIndex)
                // Dream Recorder dissolve: the next scene surfaces slowly, the last one lets go sooner.
                .transition(.asymmetric(insertion: .opacity.animation(.easeOut(duration: 1.5)),
                                        removal: .opacity.animation(.easeOut(duration: 0.9))))
        }
        .animation(.easeOut(duration: 1.5), value: sceneIndex)
        .saturation(0.85)
        .brightness(-0.04)
        .frame(height: 310)
        .frame(maxWidth: .infinity)
        .clipped()
        .mask {
            LinearGradient(stops: [.init(color: .black, location: 0), .init(color: .black, location: 0.62),
                                   .init(color: .clear, location: 1)], startPoint: .top, endPoint: .bottom)
        }
        .overlay { GrainOverlay(opacity: 0.2) }
        .ignoresSafeArea(edges: .top)
        .accessibilityHidden(true)
    }

    @ViewBuilder private var filmMedia: some View {
        let focus = UnitPoint(x: 0.38, y: 0.58)
        let scene = scenes.indices.contains(sceneIndex) ? scenes[sceneIndex] : nil
        if let scene, scene.hasMedia {
            if let video = scene.videoPath {
                StoryVideo(path: video, thumbPath: scene.thumbPath)
            } else if let image = scene.imagePath {
                StoryImage(path: image, focus: focus)
            } else if let thumb = scene.thumbPath {
                thumbImage(thumb)
            }
        } else if let video = message.story?.videoPath {
            StoryVideo(path: video, thumbPath: message.story?.thumbPath)
        } else if let image = message.story?.imagePaths?.first {
            StoryImage(path: image, focus: focus)
        } else if let thumb = message.story?.thumbPath {
            thumbImage(thumb)
        }
    }

    private func thumbImage(_ path: String) -> some View {
        AsyncImage(url: session.videoURL(path)) { phase in
            if case .success(let image) = phase { image.resizable().scaledToFill() } else { Color.night }
        }
    }

    /// Her words, one paragraph per beat. The beat being spoken is lit; the rest wait in fog.
    @ViewBuilder private var prose: some View {
        if hasBeats {
            VStack(alignment: .leading, spacing: 16) {
                ForEach(Array(scenes.enumerated()), id: \.offset) { i, scene in
                    beat(scene.textEn ?? "", index: i)
                }
            }
        } else {
            emphasized(message.translation ?? "", size: 21, color: .words, emColor: .wordsEm)
                .lineSpacing(4)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func beat(_ text: String, index i: Int) -> some View {
        let lit = beatIndex == nil || beatIndex == i
        return ZStack(alignment: .topLeading) {
            emphasized(text, size: 21, color: .fog, emColor: .fog)
                .accessibilityHidden(true)
            // Crossfading a lit copy over a dim one animates reliably where Text colour does not.
            emphasized(text, size: 21, color: .words, emColor: .wordsEm)
                .opacity(lit ? 1 : 0)
        }
        .lineSpacing(4)
        .frame(maxWidth: .infinity, alignment: .leading)
        .animation(.easeInOut(duration: 0.6), value: lit)
        .contentShape(.rect)
        .onTapGesture { play(from: i) }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Plays the story from here")
        .id(i)
    }

    private func play(from i: Int) {
        guard Self.simulated == nil, scenes.indices.contains(i) else { return }
        let start = scenes[i].start ?? 0
        if !playingTranslation {
            guard let src = session.translatedSource(message) else { return }
            session.player.play(src, key: translatedKey)
        }
        session.player.seek(to: start)
    }

    private var dayHead: some View {
        HStack(alignment: .lastTextBaseline, spacing: 16) {
            Text("\(Almanac.dayNumber(message.date))")
                .font(.serif(80, relativeTo: .largeTitle))
                .tracking(-2.4)
                .monospacedDigit()
                .foregroundStyle(Color.cream)
            VStack(alignment: .leading, spacing: 6) {
                Text(Almanac.weekdayMonth(message.date))
                    .font(.serif(19))
                    .foregroundStyle(Color.fog)
                Text(Almanac.dateEn(message.date))
                    .tinyCaps()
            }
            .padding(.bottom, 2)
        }
        .padding(.bottom, 6)
        .accessibilityElement(children: .combine)
    }

    private var track: some View {
        let total = (playingTranslation ? session.player.duration : nil) ?? Almanac.duration(message)
        let progress = following ? self.progress : 0
        return VStack(spacing: 10) {
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Color.cream.opacity(0.18)
                    Color.cream.opacity(0.75).frame(width: geo.size.width * progress)
                }
            }
            .frame(height: 1)
            HStack {
                Text(formatDuration(total * progress))
                Spacer()
                Text(formatDuration(total))
            }
            .font(.sans(12))
            .monospacedDigit()
            .foregroundStyle(Color.fog)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Translation playing")
        .accessibilityValue("\(Int(progress * 100)) percent")
    }

    private var foot: some View {
        let playingOriginal = session.player.isPlaying && session.player.currentKey == originalKey
        return HStack(alignment: .firstTextBaseline) {
            Button(playingOriginal ? "Back to English" : "Hear her original") {
                if playingOriginal, let src = session.translatedSource(message) {
                    session.player.play(src, key: translatedKey)
                } else if let src = session.originalSource(message) {
                    session.player.play(src, key: originalKey)
                }
            }
            .font(.serifItalic(20))
            .foregroundStyle(Color.wordsEm)
            .dottedUnderline(.wordsEm)
            Spacer()
            Button(action: writeBack) {
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("Write back").font(.serif(21)).foregroundStyle(Color.cream)
                    Text("to \(session.partnerName)").tinyCaps()
                }
            }
        }
        .buttonStyle(PressStyle())
        .frame(minHeight: 44)
    }
}
