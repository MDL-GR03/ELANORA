import { createRouter, createWebHistory } from 'vue-router';
import { useEventMessageStore } from '@stores/eventMessage.js';
import { useUserStore } from '@stores/user.js';
import { useProjectStore } from '@stores/project.js';
import setupService from '@/api/service/setupService';
import {
  hasProjectCapability,
  hasProjectPermission,
} from '@/utils/authorization';

import DefaultLayout from '@/layouts/DefaultLayout.vue';

const HomePage = () => import('@views/HomePage.vue');
const LoginPage = () => import('@views/LoginPage.vue');
const RegisterPage = () => import('@views/RegisterPage.vue');
const ForgotPassword = () => import('@views/ForgotPassword.vue');
const ResetPassword = () => import('@views/ResetPassword.vue');
const EmailVerificationPage = () => import('@views/EmailVerificationPage.vue');
const ContactPage = () => import('@views/ContactPage.vue');
const HTTPStatusPage = () => import('@views/HTTPStatusPage.vue');
const ProjectsPage = () => import('@views/ProjectsPage.vue');
const UploadPage = () => import('@views/UploadPage.vue');
const PendingUploadPage = () => import('@views/PendingUploadPage.vue');
const AdminInvitationsPage = () => import('@views/AdminInvitationsPage.vue');
const InvitationResponsePage = () =>
  import('@views/InvitationResponsePage.vue');
const InvitationDecisionPage = () =>
  import('@views/InvitationDecisionPage.vue');
const TiersPage = () => import('@views/TiersPage.vue');
const ProjectConfigurationPage = () =>
  import('@views/ProjectConfigurationPage.vue');
const ProfilePage = () => import('@views/ProfilePage.vue');
const SetupPage = () => import('@views/SetupPage.vue');
const OperationsPage = () => import('@views/OperationsPage.vue');

const authenticatedPageLoaders = [
  HomePage,
  ProjectsPage,
  UploadPage,
  PendingUploadPage,
  AdminInvitationsPage,
  TiersPage,
  ProjectConfigurationPage,
  ProfilePage,
  OperationsPage,
];

// Define routes
const routes = [
  // Public routes
  {
    path: '/setup',
    name: 'SetupPage',
    component: SetupPage,
  },
  {
    path: '/',
    name: 'LoginPage',
    component: LoginPage,
  },
  {
    path: '/register',
    name: 'RegisterPage',
    component: RegisterPage,
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: ForgotPassword,
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: ResetPassword,
  },
  {
    path: '/verify-email',
    name: 'EmailVerificationPage',
    component: EmailVerificationPage,
  },
  {
    path: '/contact',
    name: 'ContactPage',
    component: ContactPage,
  },
  // Invitation response routes (public, for email links)
  {
    path: '/invitation/:action/:invitationId',
    name: 'InvitationResponse',
    component: InvitationResponsePage,
    props: true,
    meta: { requiresAuth: true },
  },
  // Invitation decision page (for notifications)
  {
    path: '/invitation/respond/:invitationId',
    name: 'InvitationDecision',
    component: InvitationDecisionPage,
    props: true,
    meta: { requiresAuth: true },
  },
  // Authenticated routes with layout
  {
    path: '/',
    component: DefaultLayout,
    children: [
      {
        path: 'homePage',
        name: 'HomePage',
        component: HomePage,
        meta: { requiresAuth: true },
      },
      {
        path: 'projects',
        name: 'ProjectsPage',
        component: ProjectsPage,
        meta: { requiresAuth: true },
      },
      {
        path: 'admin/invitations',
        name: 'AdminInvitationsPage',
        component: AdminInvitationsPage,
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'admin/operations',
        name: 'OperationsPage',
        component: OperationsPage,
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'upload',
        name: 'UploadPage',
        component: UploadPage,
        meta: { requiresAuth: true, minimumProjectPermission: 'write' },
      },
      {
        path: 'contribution',
        name: 'PendingUpload',
        component: PendingUploadPage,
        meta: { requiresAuth: true, minimumProjectPermission: 'read' },
      },
      {
        path: 'tiers',
        name: 'TiersPage',
        component: TiersPage,
        meta: { requiresAuth: true, minimumProjectPermission: 'read' },
      },
      {
        path: '/projects/:projectId/configuration',
        name: 'ProjectConfigurationPage',
        component: ProjectConfigurationPage,
        meta: { requiresAuth: true, projectConfigurationAccess: true },
      },
      {
        path: 'profile',
        name: 'ProfilePage',
        component: ProfilePage,
        meta: { requiresAuth: true },
      },
      {
        path: 'error/:statusCode',
        name: 'HTTPStatusPage',
        props: (route) => ({
          statusCode: Number(route.params.statusCode),
          message: getErrorMessage(route.params.statusCode),
        }),
        component: HTTPStatusPage,
      },
      {
        // Catch-all to redirect to 404 page when no route matches
        path: '/:catchAll(.*)',
        redirect: '/error/404',
      },
    ],
  },
];

// Function to map status codes to messages
function getErrorMessage(status) {
  const messages = {
    400: '400',
    401: '401',
    403: '403',
    404: '404',
    405: '405',
    408: '408',
    500: '500',
    502: '502',
    503: '503',
  };
  return messages[status] || 'An unknown error occurred.';
}

// Create the router instance
const router = createRouter({
  history: createWebHistory(),
  routes,
});

let setupStatusPromise;

function getSetupStatus() {
  setupStatusPromise ||= setupService.getStatus().catch((error) => {
    setupStatusPromise = undefined;
    throw error;
  });
  return setupStatusPromise;
}

// Helper: handle not authenticated
function handleNotAuthenticated(eventMessageStore, to, next) {
  localStorage.setItem('redirectAfterLogin', to.fullPath);
  eventMessageStore.addMessage('http_status.401', 'warning');
  next({ name: 'LoginPage' });
}

// Global route guard
router.beforeEach(async (to, from, next) => {
  const eventMessageStore = useEventMessageStore();
  const userStore = useUserStore();
  const needsAuthCheck =
    to.meta.requiresAuth || to.meta.requiresAdmin || to.name === 'LoginPage';
  const authenticationPromise =
    needsAuthCheck && !userStore.authState.initialized
      ? userStore.verifyAuthentication()
      : Promise.resolve(userStore.isAuthenticated);

  try {
    // These independent bootstrap requests must not form a network waterfall.
    const [setupStatus] = await Promise.all([
      getSetupStatus(),
      authenticationPromise,
    ]);
    if (!setupStatus.initialized && to.name !== 'SetupPage') {
      return next({ name: 'SetupPage' });
    }
    if (setupStatus.initialized && to.name === 'SetupPage') {
      return next({
        name: userStore.isAuthenticated ? 'HomePage' : 'LoginPage',
      });
    }
  } catch (error) {
    console.error('Unable to determine installation status:', error);
  }

  // Always wait for authentication to be initialized before allowing navigation to public auth pages
  const publicAuthPages = [
    'LoginPage',
    'RegisterPage',
    'ForgotPassword',
    'ResetPassword',
    'EmailVerificationPage',
  ];
  if (publicAuthPages.includes(to.name)) {
    // If auth state is not initialized, verify authentication first
    if (!userStore.authState.initialized) {
      await userStore.verifyAuthentication();
    }
    // If authenticated, block access
    if (userStore.isAuthenticated) {
      eventMessageStore.addMessage('event_messages.already_logged_in', 'info');
      if (from.name) return next(false);
      return next({ name: 'HomePage' });
    }
  }

  // Only verify authentication if we need it for this route
  if (needsAuthCheck && !userStore.authState.initialized) {
    await userStore.verifyAuthentication();
  }

  // Check auth for protected routes
  if (to.meta.requiresAuth) {
    if (!userStore.isAuthenticated) {
      return handleNotAuthenticated(eventMessageStore, to, next);
    } else {
      const projectStore = useProjectStore();
      if (!projectStore.initialized) {
        // Project data is hydrated from local storage before routing. Refresh it
        // without blocking the navigation; project-dependent screens expose
        // their own loading state when there is no cached data.
        void projectStore
          .ensureProjects()
          .then((projects) => {
            if (projects.length) {
              // Load saved currentProject from localStorage if it exists
              const savedCurrentProject =
                localStorage.getItem('currentProject');
              if (savedCurrentProject) {
                projectStore.currentProject = JSON.parse(savedCurrentProject);
              } else if (!projectStore.currentProject) {
                // Fallback: set to the first project (sorted by setProjects)
                projectStore.setCurrentProject(projects[0]);
              }
            }
          })
          .catch((error) => console.error('Failed to fetch projects:', error));
      }
    }
  }

  // Check admin role for admin routes
  if (to.meta.requiresAdmin) {
    if (!userStore.user?.role || userStore.user.role !== 'admin') {
      eventMessageStore.addMessage('http_status.403', 'error');
      return next({ name: 'HomePage' });
    }
  }

  if (to.meta.minimumProjectPermission && userStore.user?.role !== 'admin') {
    const projectStore = useProjectStore();
    const projects = await projectStore.ensureProjects();
    const routeProjectId = Number(to.params.projectId || 0);
    const project = routeProjectId
      ? projects.find((item) => item.project_id === routeProjectId)
      : projectStore.currentProject;
    if (
      !hasProjectPermission(
        userStore.user,
        project,
        to.meta.minimumProjectPermission
      )
    ) {
      eventMessageStore.addMessage('http_status.403', 'error');
      return next({ name: 'ProjectsPage' });
    }
  }

  if (to.meta.projectConfigurationAccess) {
    const projectStore = useProjectStore();
    const projects = await projectStore.ensureProjects();
    const project = projects.find(
      (item) => item.project_id === Number(to.params.projectId)
    );
    const allowed =
      hasProjectPermission(userStore.user, project, 'admin') ||
      hasProjectCapability(userStore.user, project, 'manage_protocols');
    if (!allowed) {
      eventMessageStore.addMessage('http_status.403', 'error');
      return next({ name: 'ProjectsPage' });
    }
  }

  next();
});

let authenticatedRoutesPrefetched = false;

function prefetchAuthenticatedRoutes() {
  if (authenticatedRoutesPrefetched) return;
  authenticatedRoutesPrefetched = true;
  void Promise.allSettled(authenticatedPageLoaders.map((load) => load()));
}

// Add afterEach to track last successful route for redirectTo
router.afterEach((to, from) => {
  if (to.meta.requiresAuth) {
    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(prefetchAuthenticatedRoutes, {
        timeout: 2000,
      });
    } else {
      window.setTimeout(prefetchAuthenticatedRoutes, 250);
    }
  }
  // Don't update redirectTo if navigating to or coming from the HTTPStatus error page
  if (to.name !== 'HTTPStatusPage' && from.name !== 'HTTPStatusPage') {
    localStorage.setItem('redirectTo', from.fullPath || '/');
  }
  // If user navigates from LoginPage to HomePage, update redirectAfterLogin to homepage
  if (from.name === 'LoginPage' && to.name === 'HomePage') {
    localStorage.setItem('redirectAfterLogin', '/');
  }
});

export default router;
