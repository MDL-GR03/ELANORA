<template>
  <ol v-if="item.comments.length" class="discussion">
    <li v-for="comment in item.comments" :key="comment.comment_id">
      <div>
        <strong>{{ comment.author_name }}</strong
        ><time>{{ formatDate(comment.created_at) }}</time>
      </div>
      <p>{{ comment.body }}</p>
    </li>
  </ol>
  <form
    v-if="
      canComment &&
      !isFinished(item.state) &&
      revisionFeedbackCaseId !== item.case_id
    "
    class="reply"
    @submit.prevent="addComment(item)"
  >
    <label :for="`reply-${item.case_id}`">{{
      t('reviewCases.discussion.add')
    }}</label>
    <div>
      <input
        :id="`reply-${item.case_id}`"
        v-model.trim="replies[item.case_id]"
        required
        maxlength="10000"
        :placeholder="t('reviewCases.discussion.placeholder')"
      />
      <button type="submit" :disabled="busy">
        {{ t('reviewCases.discussion.comment') }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { useReviewCaseContext } from './reviewCaseContext';

defineProps({
  item: { type: Object, required: true },
});

const {
  addComment,
  busy,
  canComment,
  formatDate,
  isFinished,
  replies,
  revisionFeedbackCaseId,
  t,
} = useReviewCaseContext();
</script>
