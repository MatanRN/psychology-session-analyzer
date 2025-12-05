from models import PatientRelationship, TranscriptAnalysis


def get_positive_and_negative_topics(
    analysis: TranscriptAnalysis,
) -> tuple[list[str], list[str]]:
    positive_topics: list[str] = []
    negative_topics: list[str] = []

    if not analysis.utterances:
        return positive_topics, negative_topics

    for utterance in analysis.utterances:
        if utterance.role == "patient":
            if utterance.sentiment_score > 0:
                positive_topics.extend(utterance.topic)
            elif utterance.sentiment_score < 0:
                negative_topics.extend(utterance.topic)

    return positive_topics, negative_topics


def get_sentiment_scores(
    analysis: TranscriptAnalysis,
) -> list[float]:
    sentiment_scores: list[float] = []
    if not analysis.utterances:
        return sentiment_scores
    for utterance in analysis.utterances:
        sentiment_scores.append(utterance.sentiment_score)
    return sentiment_scores


def get_patient_relationships(
    analysis: TranscriptAnalysis,
) -> list[PatientRelationship]:
    patient_relationships: list[PatientRelationship] = []
    if not analysis.relationships:
        return patient_relationships
    for relationship in analysis.relationships:
        patient_relationships.append(relationship)
    return patient_relationships
